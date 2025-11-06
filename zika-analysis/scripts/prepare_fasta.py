import pandas as pd
import sys

# Define file paths based on the Snakemake rule inputs/outputs
SEQUENCE_TABLE_PATH = 'data/book2_sequence.fasta'
METADATA_PATH = 'data/toxoplasma_metadata.tsv'
OUTPUT_FASTA_PATH = 'results/sequences_for_augur.fasta'

try:
    # 1. Load the sequence data (now confirmed working)
    sequence_table = pd.read_csv(SEQUENCE_TABLE_PATH, sep=None, engine='python')
    sequence_map = sequence_table.set_index('strain')['Seq'].to_dict()

    # 2. Load the metadata (Now using the clean file name)
    metadata = pd.read_csv(METADATA_PATH, sep='\t')

    # *** FINAL FIX: STRIP WHITESPACE FROM COLUMN NAMES ***
    metadata.columns = metadata.columns.str.strip()
    # ******************************************************

    # 3. Generate the final FASTA file (This block must be indented!)
    with open(OUTPUT_FASTA_PATH, 'w') as f:
        # Loop through every row in the metadata file
        for index, row in metadata.iterrows():
            strain_id = row['IDs']
            # Note: This 'strain' column is the link to your sequence table
            seq_key = row['strain']

            if seq_key in sequence_map:
                sequence = sequence_map[seq_key]
                # Write the unique FASTA entry: >Strain_ID followed by sequence
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