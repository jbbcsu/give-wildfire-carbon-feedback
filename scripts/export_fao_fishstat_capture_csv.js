/* Export the preregistered FishStat capture table through bundled Derby JDBC.
 * Run only against a disposable database copy; the source database is never opened.
 */
var Files = Java.type("java.nio.file.Files");
var Paths = Java.type("java.nio.file.Paths");
var StandardCharsets = Java.type("java.nio.charset.StandardCharsets");
var DriverManager = Java.type("java.sql.DriverManager");

if (arguments.length !== 2) {
  throw new Error("usage: export_fao_fishstat_capture_csv.js DATABASE_COPY OUTPUT_CSV");
}
var database = String(arguments[0]);
var output = Paths.get(String(arguments[1]));
Files.createDirectories(output.getParent());
Java.type("java.lang.Class").forName("org.apache.derby.jdbc.EmbeddedDriver");

var columns = ["COUNTRY", "SPECIES", "AREA", "MEASURE"];
for (var year = 1950; year <= 2024; year++) {
  columns.push("VALUE_Y" + year);
  columns.push("SYMBOL_Y" + year);
}

function csv(value) {
  if (value === null) return "";
  var text = String(value);
  if (/[,"]|\r|\n/.test(text)) return '"' + text.replace(/"/g, '""') + '"';
  return text;
}

var connection = DriverManager.getConnection("jdbc:derby:" + database);
connection.setReadOnly(true);
var statement = connection.createStatement();
var sql = "SELECT " + columns.join(",") + " FROM TSD_CAPTURE_QUANTITY ORDER BY COUNTRY,SPECIES,AREA,MEASURE";
var result = statement.executeQuery(sql);
var writer = Files.newBufferedWriter(output, StandardCharsets.UTF_8);
var rows = 0;
try {
  writer.write(columns.join(","));
  writer.write("\n");
  while (result.next()) {
    var fields = [];
    for (var index = 1; index <= columns.length; index++) fields.push(csv(result.getString(index)));
    writer.write(fields.join(","));
    writer.write("\n");
    rows++;
  }
} finally {
  writer.close();
  result.close();
  statement.close();
  connection.close();
}
print("exported " + rows + " FishStat capture records to " + output);
