NextStrain Framework for Toxoplasma gondii GRA6

"Explain what the Respository is for"


Follow steps to installing NextStrain software:
https://docs.nextstrain.org/en/latest/install.html 

Run sample phylogenetic workflow:
https://docs.nextstrain.org/en/latest/tutorials/running-a-phylogenetic-workflow.html

STEPS FOR THE REST:

Files needed to provide:

metadata.tsv (Provide at least "strain" "country" "date") -- Make sure all labels are lowercase
outgroup.gb (Downloadable on NCBI)
.fasta (Sequence data) -- Make sure strain ID matches metadat.tsv file
colors.tsv ("Country" "Country Name" "Hexcode") -- See file for example
lat_long.tsv ("Country" "Country Name" "Latitude" "Longitude") -- See file for example

Files needed to change in repository to match data:

Snakefile (changes needed are written in green)
.json (Match key titles to metadata.tsv file)

"Explain the steps for the repository"
