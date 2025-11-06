import pandas as pd
import sys

SEQUENCE_TABLE_PATH = 'data/book2_sequence.fasta'
METADATA_PATH = 'data/toxoplasma_metadata.tsv'
OUTPUT_FASTA_PATH = 'results/sequences_for_augur.fasta'

# ... (rest of the imports/paths) ...

# ... (in scripts/prepare_fasta.py) ...
try:
    # 1. Load the sequence data (confirmed working)
    sequence_table = pd.read_csv(SEQUENCE_TABLE_PATH, sep=None, engine='python')
    sequence_map = sequence_table.set_index('strain')['Seq'].to_dict()

    # 2. Load the metadata: Use regex for separator to handle multiple spaces/tabs (Universal Whitespace Separator)
    # This will load the file, but will create many extra columns that need merging.
# 2. Load the metadata
    metadata = pd.read_csv(METADATA_PATH, sep='\t')

    # --- DEBUG LINE ADDED ---
    print(f"DEBUG: Columns found in METADATA file after aggressive load: {metadata.columns.tolist()}", file=sys.stderr)
    # *************************

    # 3. Consolidate the References Column (Using positional index based on 13 expected headers)

    # Since there are 13 original headers, the last valid column is at index 12.
    LAST_VALID_INDEX = 12
    REFERENCE_COLUMN_NAME = metadata.columns[LAST_VALID_INDEX]

    # Identify the columns that need to be merged (everything after the 13th column)
    cols_to_merge = metadata.columns[LAST_VALID_INDEX:]

    # Consolidate all text in these columns into the last valid column (Reference)
    metadata[REFERENCE_COLUMN_NAME] = metadata[cols_to_merge].astype(str).agg(' '.join, axis=1)

    # Drop the extra, now-redundant columns
    metadata = metadata.drop(columns=cols_to_merge[1:])

    # 4. Generate the final FASTA file
    # ... (rest of the script) ...

    with open(OUTPUT_FASTA_PATH, 'w') as f:
        for index, row in metadata.iterrows():
            strain_id = row['IDs']
            seq_key = row['strain']

            if seq_key in sequence_map:
                sequence = sequence_map[seq_key]
                f.write(f">{strain_id}\n{sequence}\n")
            else:
                sys.stderr.write(f"Warning: No sequence found for key: {seq_key} (Metadata ID: {strain_id})\n")

# ... (the rest of the script, including the except blocks, remains) ...

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
