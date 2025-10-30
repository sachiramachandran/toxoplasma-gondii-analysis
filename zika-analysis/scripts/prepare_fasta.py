import pandas as pd
import sys

SEQUENCE_TABLE_PATH = 'data/book2_sequence.fasta'
METADATA_PATH = 'data/toxo_rflp_1662_metadata.tsv'
OUTPUT_FASTA_PATH = 'results/sequences_for_augur.fasta'

# ... (rest of the imports/paths) ...

try:
    # 1. Load the tabular sequence data (using flexible separator detection)
    # Using sep=None, engine='python' lets pandas try to figure out the spacing/tabs.
    sequence_table = pd.read_csv(SEQUENCE_TABLE_PATH, sep=None, engine='python')

    # --- DEBUG LINE ---
    print(f"DEBUG: Columns found in sequence file: {sequence_table.columns.tolist()}", file=sys.stderr)
    # ------------------

    # Map strain (ID) to sequence ('Seq'). We try to use the name 'strain' and 'Seq'.
    sequence_map = sequence_table.set_index('strain')['Seq'].to_dict()

    # 2. Load the metadata
    metadata = pd.read_csv(METADATA_PATH, sep='\t')

    with open(OUTPUT_FASTA_PATH, 'w') as f:
        for index, row in metadata.iterrows():
            strain_id = row['IDs']
            seq_key = row['strain']

            if seq_key in sequence_map:
                sequence = sequence_map[seq_key]
                f.write(f">{strain_id}\n{sequence}\n")
            else:
                sys.stderr.write(f"Warning: No sequence found for key: {seq_key} (Metadata ID: {strain_id})\n")

except FileNotFoundError as e:
    sys.stderr.write(f"Error: Required file not found: {e.filename}\n")
    sys.exit(1)
except KeyError as e:
    sys.stderr.write(f"Error: Column {e} not found. Check column names in your input files.\n")
    sys.exit(1)

print(f"New FASTA file '{OUTPUT_FASTA_PATH}' successfully created.")
