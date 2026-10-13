const MEMORY_GUARD_RUNNER = joinpath(@__DIR__, "compare_agriculture_replacement.jl")
include(MEMORY_GUARD_RUNNER)

const MAX_RSS_BYTES = 512 * 1024^2
const PROCESS_PEAK_RSS_BYTES = Sys.maxrss()
println("process_peak_rss_bytes=$PROCESS_PEAK_RSS_BYTES")
println("max_rss_bytes=$MAX_RSS_BYTES")
PROCESS_PEAK_RSS_BYTES <= MAX_RSS_BYTES || error("512 MiB RSS cap exceeded")

open(joinpath(OUTPUT_DIR, "run_metadata.csv"), "w") do io
    println(io, "julia_version,julia_threads,pulse_year,pulse_size,seed,draws,process_peak_rss_bytes,max_rss_bytes")
    println(io, join((VERSION, Threads.nthreads(), PULSE_YEAR, PULSE_SIZE, SEED, N, PROCESS_PEAK_RSS_BYTES, MAX_RSS_BYTES), ","))
end
