import pandas as pd
import sys

SEQUENCE_TABLE_PATH = 'data/book2_sequence.fasta'
METADATA_PATH = 'data/toxo_rflp_1662_metadata.tsv'
OUTPUT_FASTA_PATH = 'results/sequences_for_augur.fasta'

# ... (rest of the imports/paths) ...

try:
    # 1. Load the sequence data (confirmed working from previous debug)
    sequence_table = pd.read_csv(SEQUENCE_TABLE_PATH, sep=None, engine='python')
    sequence_map = sequence_table.set_index('strain')['Seq'].to_dict()

    # 2. Load the metadata (Handle split 'Reference' column)
    # Load the metadata file without auto-detecting column count to prevent ParserError.
    # We will let pandas assign headers to the extra columns.
    metadata = pd.read_csv(
        METADATA_PATH,
        sep='\t',
        header=0,
        # Setting names=None ensures it uses the file's header row
    )

    # 3. Consolidate the References Column

    # Find the index of the 'Reference' column.
    # Note: If your column is named 'References', use that instead. We use 'Reference' based on the visual.
    ref_col_index = metadata.columns.get_loc('Reference')

    # Identify the columns that need to be merged (everything from 'Reference' onwards)
    cols_to_merge = metadata.columns[ref_col_index:]

    # Consolidate all text in these columns into the first column ('Reference')
    metadata['Reference'] = metadata[cols_to_merge].astype(str).agg(' '.join, axis=1)

    # Drop the extra, now-redundant columns (all columns after the original 'Reference' header)
    metadata = metadata.drop(columns=cols_to_merge[1:])

    # 4. Generate the final FASTA file (The Strain ID lookup logic)
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
