# vopd
Code supporting the "Monitoring Hate Speech in the US Media" project, of Prof. Babak Bahador's group in the GW School of Media and Public Affairs.

## Running the program

usage: `python vopd.py [-h] [--window WINDOW] [--context CONTEXT] [--ask] transcript`

```positional arguments:
  transcript         filepath to transcript pdf or directory

optional arguments:
  -h, --help         show this help message and exit
  --window WINDOW    number of words that subject and keyword must be within (default = 10)
  --context CONTEXT  number of words before and after subject and keyword to extract (default = 20)
  --subjectfile SUBJECTFILE   subject list file (default = subjects.csv)
  --keywordfile KEYWORDFILE   keyword list file (default = keywords.csv)
  --normalizefile NORMALIZEFILE   normalize terms file (default = normalize_terms.csv)
  --suppress-lone-subjects    do not write rows for subjects found but not co-located with keywords
  --suppress-lone-keywords    do not write rows for keywords found but not co-located with subjects

```

Transcript files must be named using the following pattern:

`MM_DD_YYYY_NNN_Name Of The Show.pdf`

where:
 - `MM_DD_YYYY` is the date of the show
 - `NNN` is the show code/number
(any separator character is okay - but positions of the values are important)


## Output files

**`extracts.csv`** - All instances of a keyword and a subject found within "n" number
of words of each other, where "n" is the configured window size.

Note that if `extracts.csv` already exists, it will be appended to.  If you wish to overwrite, simply delete or rename `extracts.csv`.


## recycle_keywords.py utility

The `recycle_keywords.py` utility takes:
- A coding file (default `coding.csv`)
- A keywords file (default `keywords.csv`)
- A normalize_terms file (default `normalize_terms.csv`)

It scans through the coding file, looking for keyword severity scores assigned by the human coder, as well as looking for new keywords added by the human coder.  It then updates the scores of existing keywords (using the mode of human-assigned severity scores), and adds new keywords, to the keywords file.


