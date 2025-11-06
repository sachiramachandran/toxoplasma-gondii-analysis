import pandas as pd
import sys

SEQUENCE_TABLE_PATH = 'data/book2_sequence.fasta'
METADATA_PATH = 'data/toxoplasma_metadata.tsv'
OUTPUT_FASTA_PATH = 'results/sequences_for_augur.fasta'

# ... (rest of the imports/paths) ...

# ... (in scripts/prepare_fasta.py) ...
# ... (in scripts/prepare_fasta.py) ...
try:
    # 1. Load the sequence data (now confirmed working)
    sequence_table = pd.read_csv(SEQUENCE_TABLE_PATH, sep=None, engine='python')
    sequence_map = sequence_table.set_index('strain')['Seq'].to_dict()

    # 2. Load the metadata (Now using the clean file name)
    metadata = pd.read_csv(METADATA_PATH, sep='\t')

    # *** FINAL FIX: STRIP WHITESPACE FROM COLUMN NAMES ***
    metadata.columns = metadata.columns.str.strip()
    # ******************************************************

    # 3. Generate the final FASTA file (rest of the script)
    with open(OUTPUT_FASTA_PATH, 'w') as f:
        # ... (FASTA generation logic that references 'IDs' and 'strain') ...

# ... (the rest of the script, including the except blocks, remains) ...
except FileNotFoundError as e:
    sys.stderr.write(f"Error: Required file not found: {e.filename}\n")
    sys.exit(1)
except KeyError as e:
    sys.stderr.write(f"Error: Column {e} not found. Check column names in your input files.\n")
    sys.exit(1)

print(f"New FASTA file '{OUTPUT_FASTA_PATH}' successfully created.")
