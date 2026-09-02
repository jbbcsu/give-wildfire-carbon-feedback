/*
 * Deterministically export the FAO FishStat capture table from a disposable
 * read-only Derby copy. Run with the FishStatJ-bundled Java 11 Nashorn shell.
 */
var DriverManager = Java.type('java.sql.DriverManager');
var Files = Java.type('java.nio.file.Files');
var Paths = Java.type('java.nio.file.Paths');
var StandardCharsets = Java.type('java.nio.charset.StandardCharsets');
var StandardCopyOption = Java.type('java.nio.file.StandardCopyOption');
var MessageDigest = Java.type('java.security.MessageDigest');
var BufferedWriter = Java.type('java.io.BufferedWriter');
var OutputStreamWriter = Java.type('java.io.OutputStreamWriter');
var FileOutputStream = Java.type('java.io.FileOutputStream');
var BigInteger = Java.type('java.math.BigInteger');
var ReflectArray = Java.type('java.lang.reflect.Array');
var Byte = Java.type('java.lang.Byte');
var JavaString = Java.type('java.lang.String');

if (arguments.length !== 3) {
  throw new Error('usage: export_fao_fishstat_capture_wide.js DERBY_DB OUTPUT_CSV SOURCE_AUDIT_JSON');
}

var dbPath = String(arguments[0]);
var outputPath = Paths.get(String(arguments[1])).toAbsolutePath();
var auditPath = Paths.get(String(arguments[2])).toAbsolutePath();
var outputPart = Paths.get(String(arguments[1]) + '.part').toAbsolutePath();
var auditPart = Paths.get(String(arguments[2]) + '.part').toAbsolutePath();
Files.createDirectories(outputPath.getParent());
Files.createDirectories(auditPath.getParent());

var YEARS = [];
for (var year = 1950; year <= 2024; year++) YEARS.push(year);
var ALLOWED_STATUS = {};
'A B E F G I P S U V X L M N O Q'.split(' ').forEach(function(x) { ALLOWED_STATUS[x] = true; });

function csv(value) {
  var s = value === null || value === undefined ? '' : String(value);
  return '"' + s.replace(/"/g, '""') + '"';
}

function sha256(path) {
  var digest = MessageDigest.getInstance('SHA-256');
  var stream = Files.newInputStream(path);
  var buffer = ReflectArray.newInstance(Byte.TYPE, 1024 * 1024);
  try {
    var n;
    while ((n = stream.read(buffer)) !== -1) digest.update(buffer, 0, n);
  } finally {
    stream.close();
  }
  return String(JavaString.format('%064x', new BigInteger(1, digest.digest())));
}

Java.type('java.lang.Class').forName('org.apache.derby.jdbc.EmbeddedDriver');
var conn = DriverManager.getConnection('jdbc:derby:' + dbPath);
conn.setReadOnly(true);

var valueColumns = [];
YEARS.forEach(function(y) { valueColumns.push('T.VALUE_Y' + y); valueColumns.push('T.SYMBOL_Y' + y); });
var sql = [
  'SELECT T.ID, T.COUNTRY, C.ISO_3_CODE, C.NAME_EN,',
  'T.SPECIES, S.SCIENTIFIC_NAME, S.NAME_EN,',
  'T.AREA, A.NAME_EN, IM.NAME_EN,',
  'T.MEASURE, M.NAME_EN, M.UNIT, M.UNIT_MULTIPLIER,',
  valueColumns.join(', '),
  'FROM FISHSTAT.TSD_CAPTURE_QUANTITY T',
  'JOIN FISHSTAT.REF_COUNTRY C ON C.UN_CODE = T.COUNTRY',
  'JOIN FISHSTAT.REF_SPECIES S ON S.ALPHA_3_CODE = T.SPECIES',
  'JOIN FISHSTAT.REF_AREA A ON A.CODE = T.AREA',
  'JOIN FISHSTAT.REL_INLAND_MARINE_AREA R ON R.CHILD_ID = A.ID',
  'JOIN FISHSTAT.REF_INLAND_MARINE IM ON IM.ID = R.PARENT_ID',
  'JOIN FISHSTAT.REF_MEASURE M ON M.CODE = T.MEASURE',
  'ORDER BY T.ID'
].join(' ');

var header = [
  'source_record_id', 'country_un_m49', 'country_iso3', 'country_name',
  'species_asfis_code', 'species_scientific_name', 'species_name',
  'fao_area_code', 'fao_area_name', 'environment_class',
  'measure_code', 'measure_name', 'unit', 'unit_multiplier'
];
YEARS.forEach(function(y) { header.push('value_' + y); header.push('status_' + y); });

var counts = {
  wide_records: 0,
  annual_cells: 0,
  value_null_cells: 0,
  status_blank_cells: 0,
  positive_value_cells: 0,
  zero_value_cells: 0,
  environment_records: {inland: 0, marine: 0},
  measure_records: {},
  status_cells: {}
};

var writer = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(outputPart.toFile()), StandardCharsets.UTF_8));
var statement;
var result;
try {
  writer.write(header.map(csv).join(',') + '\n');
  statement = conn.createStatement();
  statement.setFetchSize(128);
  result = statement.executeQuery(sql);
  var lastId = '';
  while (result.next()) {
    var id = String(result.getString(1));
    if (lastId && id <= lastId) throw new Error('source record IDs are not strictly increasing');
    lastId = id;
    var environmentName = String(result.getString(10));
    var environmentClass = environmentName === 'Inland waters' ? 'inland' : (environmentName === 'Marine areas' ? 'marine' : '');
    if (!environmentClass) throw new Error('unknown environment class: ' + environmentName);
    var measureCode = String(result.getString(11));
    if (!(measureCode === 'Q_tlw' || measureCode === 'Q_no_1')) throw new Error('unexpected measure: ' + measureCode);
    var row = [
      id, result.getString(2), result.getString(3), result.getString(4),
      result.getString(5), result.getString(6), result.getString(7),
      result.getString(8), result.getString(9), environmentClass,
      measureCode, result.getString(12), result.getString(13), result.getString(14)
    ];
    var column = 15;
    YEARS.forEach(function(y) {
      var value = result.getString(column++);
      var status = result.getString(column++);
      counts.annual_cells++;
      if (value === null) counts.value_null_cells++;
      if (status === null || String(status).length === 0) counts.status_blank_cells++;
      if (status !== null && !ALLOWED_STATUS[String(status)]) throw new Error('unknown status code: ' + status);
      if (value !== null) {
        var numeric = Number(String(value));
        if (!isFinite(numeric) || numeric < 0) throw new Error('invalid annual value');
        if (numeric > 0) counts.positive_value_cells++; else counts.zero_value_cells++;
      }
      if (status !== null) counts.status_cells[String(status)] = (counts.status_cells[String(status)] || 0) + 1;
      row.push(value); row.push(status);
    });
    counts.wide_records++;
    counts.environment_records[environmentClass]++;
    counts.measure_records[measureCode] = (counts.measure_records[measureCode] || 0) + 1;
    writer.write(row.map(csv).join(',') + '\n');
  }
} finally {
  if (result) result.close();
  if (statement) statement.close();
  conn.close();
  writer.close();
}

if (counts.wide_records !== 30918) throw new Error('wide record count changed: ' + counts.wide_records);
if (counts.annual_cells !== 30918 * 75) throw new Error('annual cell count changed');
if (counts.value_null_cells !== 0 || counts.status_blank_cells !== 0) throw new Error('blank value/status pair found');
Files.move(outputPart, outputPath, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
var audit = {
  schema: 'fao_fishstat_capture_headless_source_audit_v1',
  status: 'complete_wide_record_export_from_disposable_derby_copy',
  source_table: 'FISHSTAT.TSD_CAPTURE_QUANTITY',
  years: [1950, 2024],
  output: {bytes: Number(Files.size(outputPath)), sha256: sha256(outputPath)},
  counts: counts,
  boundaries: {
    fishstat_gui_menu_export_reconciled: false,
    marine_tonnage_filter_authorized: false,
    country_or_eez_allocation_authorized: false,
    fishmip_observed_calibration_authorized: false,
    welfare_translation_authorized: false,
    damage_or_scc_authorized: false
  }
};
Files.write(auditPart, new JavaString(JSON.stringify(audit, null, 2) + '\n').getBytes(StandardCharsets.UTF_8));
Files.move(auditPart, auditPath, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
print('FAO FishStat capture wide export completed: ' + counts.wide_records + ' records, ' + counts.annual_cells + ' annual cells');
