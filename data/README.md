# Data intake boundary

Do not place downloaded datasets in this repository until their license,
version, checksum, spatial units, baseline period, and processing script are
recorded.  Raw climate, flood-loss, exposure, and crop data should be stored
outside the wildfire project and fetched by reproducible scripts added here.

The first authorized input, GDHY v1.2/v1.3, is stored here in `raw/` together
with its archive and provenance record. It has been extracted to 360 NetCDF
files for feature preparation; it is not a completed estimation panel.

CRU TS 4.10 scPDSI is registered as a historical drought benchmark. A verified
partial acquisition is present, but the complete raw file is not. The
crop-stage preparation code and synthetic tests are ready; the partial and any
completed CRU file remain ignored and may be used only for historical
validation—not as a projected or matched-pulse SCC input.
