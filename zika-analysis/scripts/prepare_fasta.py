import pandas as pd
import sys

# Define file paths
SEQUENCE_TABLE_PATH = 'data/toxo_expansion.txt'
METADATA_PATH = 'data/toxo_meta3.tsv'
OUTPUT_FASTA_PATH = 'results/sequences_for_augur.fasta'

try:
    # 1. Load the sequence data (toxo_expansion.txt: 'strain' for genotype key, 'Seq' for sequence)
    # Using sep=None to handle potential mixed delimiters in the sequence file
    sequence_table = pd.read_csv(SEQUENCE_TABLE_PATH, sep=None, engine='python')

    # Strip whitespace from column headers (Fixes 'strain ' and 'Seq ')
    sequence_table.columns = sequence_table.columns.str.strip()

    # Create the sequence map: Genotype Number (strain) -> Sequence (Seq)
    sequence_map = sequence_table.set_index('strain')['Seq'].to_dict()

    # 2. Load the metadata (toxoplasma_metadata.tsv)
    metadata = pd.read_csv(METADATA_PATH, sep='\t')

    # Strip whitespace from metadata headers
    metadata.columns = metadata.columns.str.strip()

    # *** FIX 1 (FOR AUGUR FILTER): RENAME 'IDs' TO 'strain' ***
    # The 'IDs' column holds the unique name that Augur needs to see as the 'strain' identifier.
    if 'IDs' in metadata.columns:
        metadata = metadata.rename(columns={'IDs': 'strain_id_augur'})
    else:
        # If 'IDs' is not found, raise an error to stop and check headers
        raise KeyError("'IDs' column not found in metadata after stripping whitespace.")

    # Check that the Genotype Key column exists (which you named 'strain')
    if 'strain' not in metadata.columns:
        raise KeyError("'strain' (Genotype Key) column not found in metadata.")

    # 3. Generate the final FASTA file (Handles 1:many redundancy)
    with open(OUTPUT_FASTA_PATH, 'w') as f:
        for index, row in metadata.iterrows():
            # The FASTA header must be the unique ID, which is now named 'strain_id_augur'
            strain_id = row['strain_id_augur']

            # The lookup key is the genotype number (column named 'strain')
            seq_key = row['strain']

            if seq_key in sequence_map:
                sequence = sequence_map[seq_key]
                # Write the unique FASTA entry
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