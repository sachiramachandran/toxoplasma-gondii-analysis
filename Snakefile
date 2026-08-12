# Nextstrain build for Toxoplasma gondii GRA6.
#
# Adapted from nextstrain/zika-tutorial. Run from the repository root:
#
#     nextstrain build --docker .
#
# The Snakefile lives at the root rather than inside toxo-analysis/ so that the
# build can write auspice/toxoplasma-gondii-analysis.json. nextstrain.org
# serves community builds from auspice/<repo-name>.json on the default branch,
# and the Docker runtime mounts only the build directory — a Snakefile inside
# toxo-analysis/ could not reach the root auspice/ at all.

# Inputs, all relative to the repository root.
input_fasta     = "toxo-analysis/data/toxoplasma_sequences.fasta"
input_metadata  = "toxo-analysis/data/toxo_meta3.tsv"
dropped_strains = "toxo-analysis/config/dropped_strains.txt"
reference       = "toxo-analysis/config/ToxoplasmaOutgroup.gb"
colors          = "toxo-analysis/config/colors.tsv"
lat_longs       = "toxo-analysis/config/lat_longs.tsv"
auspice_config  = "toxo-analysis/config/auspice_config.json"

# Generated files.
results = "toxo-analysis/results"
logs    = "toxo-analysis/logs"
auspice = "auspice"


rule all:
    input:
        auspice_json = f"{auspice}/toxoplasma-gondii-analysis.json"


rule index_sequences:
    message:
        """
        Creating an index of sequence composition for filtering.
        """
    input:
        sequences = input_fasta
    output:
        sequence_index = f"{results}/sequence_index.tsv"
    shell:
        """
        augur index \
            --sequences {input.sequences} \
            --output {output.sequence_index}
        """

rule filter:
    message:
        """
        Filtering sequences.

        --min-date and --sequences-per-group are inherited from the Zika
        tutorial and are no-ops for this dataset: collection dates run
        1989-2018 and no year holds more than 500 isolates, so all 1,662
        sequences pass. They are kept so the thresholds are explicit if the
        dataset grows.
        """
    input:
        sequences = rules.index_sequences.input.sequences,
        sequence_index = rules.index_sequences.output.sequence_index,
        metadata = input_metadata,
        exclude = dropped_strains
    output:
        sequences = f"{results}/filtered.fasta",
        filtered_metadata = f"{results}/filtered_metadata.tsv",
        passed_strains = f"{results}/passed_strains.txt",
        filter_log = f"{logs}/filter_log.tsv"
    shell:
        """
        augur filter \
            --sequences {input.sequences} \
            --sequence-index {input.sequence_index} \
            --metadata {input.metadata} \
            --exclude {input.exclude} \
            --output-sequences {output.sequences} \
            --output-metadata {output.filtered_metadata} \
            --output-strains {output.passed_strains} \
            --output-log {output.filter_log} \
            --group-by year \
            --sequences-per-group 500 \
            --min-date 1908
        """

rule align:
    message:
        """
        Aligning sequences to {input.reference}
          - filling gaps with N
        """
    input:
        sequences = rules.filter.output.sequences,
        reference = reference
    output:
        alignment = f"{results}/aligned.fasta"
    shell:
        """
        augur align \
            --sequences {input.sequences} \
            --reference-sequence {input.reference} \
            --output {output.alignment} \
            --fill-gaps
        """

rule tree:
    message: "Building tree"
    input:
        alignment = rules.align.output.alignment
    output:
        tree = f"{results}/tree_raw.nwk"
    shell:
        """
        augur tree \
            --alignment {input.alignment} \
            --output {output.tree}
        """

rule refine:
    message:
        """
        Refining tree
          - estimate timetree
          - use {params.coalescent} coalescent timescale
          - estimate {params.date_inference} node dates
          - filter tips more than {params.clock_filter_iqd} IQDs from clock expectation

        The clock rate is retuned for a 297 bp protozoan locus; the tutorial's
        defaults assume a whole RNA virus genome.
        """
    input:
        tree = rules.tree.output.tree,
        alignment = rules.align.output.alignment,
        metadata = input_metadata
    output:
        tree = f"{results}/tree.nwk",
        node_data = f"{results}/branch_lengths.json"
    params:
        coalescent = "opt",
        date_inference = "marginal",
        clock_rate = 0.0008,
        clock_std_dev = 0.0002,
        clock_filter_iqd = 4
    shell:
        """
        augur refine \
            --tree {input.tree} \
            --alignment {input.alignment} \
            --metadata {input.metadata} \
            --output-tree {output.tree} \
            --output-node-data {output.node_data} \
            --timetree \
            --coalescent {params.coalescent} \
            --date-confidence \
            --date-inference {params.date_inference} \
            --clock-rate {params.clock_rate} \
            --clock-std-dev {params.clock_std_dev} \
            --clock-filter-iqd {params.clock_filter_iqd} \
            --keep-root
        """

rule ancestral:
    message: "Reconstructing ancestral sequences and mutations"
    input:
        tree = rules.refine.output.tree,
        alignment = rules.align.output.alignment
    output:
        node_data = f"{results}/nt_muts.json"
    params:
        inference = "joint"
    shell:
        """
        augur ancestral \
            --tree {input.tree} \
            --alignment {input.alignment} \
            --output-node-data {output.node_data} \
            --inference {params.inference}
        """

rule translate:
    message: "Translating amino acid sequences"
    input:
        tree = rules.refine.output.tree,
        node_data = rules.ancestral.output.node_data,
        reference = reference
    output:
        node_data = f"{results}/aa_muts.json"
    shell:
        """
        augur translate \
            --tree {input.tree} \
            --ancestral-sequences {input.node_data} \
            --reference-sequence {input.reference} \
            --output-node-data {output.node_data}
        """

rule traits:
    message: "Inferring ancestral traits for {params.columns!s}"
    input:
        tree = rules.refine.output.tree,
        metadata = input_metadata
    output:
        node_data = f"{results}/traits.json"
    params:
        columns = "country"
    shell:
        """
        augur traits \
            --tree {input.tree} \
            --metadata {input.metadata} \
            --output-node-data {output.node_data} \
            --columns {params.columns} \
            --confidence
        """

rule export:
    message: "Exporting data files for auspice"
    input:
        tree = rules.refine.output.tree,
        metadata = input_metadata,
        branch_lengths = rules.refine.output.node_data,
        traits = rules.traits.output.node_data,
        nt_muts = rules.ancestral.output.node_data,
        aa_muts = rules.translate.output.node_data,
        colors = colors,
        lat_longs = lat_longs,
        auspice_config = auspice_config
    output:
        auspice_json = rules.all.input.auspice_json
    shell:
        """
        augur export v2 \
            --tree {input.tree} \
            --metadata {input.metadata} \
            --node-data {input.branch_lengths} {input.traits} {input.nt_muts} {input.aa_muts} \
            --colors {input.colors} \
            --lat-longs {input.lat_longs} \
            --auspice-config {input.auspice_config} \
            --include-root-sequence \
            --output {output.auspice_json}
        """

rule clean:
    message: "Removing directories: {params}"
    params:
        results,
        logs
    shell:
        "rm -rfv {params}"
