import argparse
import datetime
import csv
import re
from nltk.tokenize import word_tokenize
import nltk
from document import *

nltk.download('punkt')

# global variables
subject_map = {}
keyword_map = {}
keyword_id = {}
subjects = []
keywords = []
normalize_terms = {}


def tokenize(transcript_text):
    # Convert to lower case
    clean_transcript_text = transcript_text.lower()
    # Split words by periods
    clean_transcript_text = re.sub(r'([a-z])\.([a-z])', r'\1. \2', clean_transcript_text)

    for term, normalized_term in normalize_terms.items():
        clean_transcript_text = clean_transcript_text.replace(term, normalized_term)
    return word_tokenize(clean_transcript_text)


def window_iter(transcript_words, window_size):
    pos = 2 - window_size
    while pos + window_size <= len(transcript_words) + window_size - 1:
        yield pos, pos + window_size, transcript_words[max(pos,0):min(pos + window_size, len(transcript_words))]
        pos += 1


def back_window_iter(transcript_words, window_size):
    pos = len(transcript_words)
    while pos - window_size >= 0:
        yield pos - window_size, pos, transcript_words[pos - window_size:pos]
        pos -= 1


def matching_word_list(words, word_list):
    for pos, word in enumerate(words):
        if word in word_list:
            return pos, word
    return None, None


def context(transcript_words, word_pos1, word_pos2, context_size=20):
    context_start = max(word_pos1 - context_size, 0)
    context_end = min(word_pos2 + context_size, len(transcript_words))
    return transcript_words[context_start:context_end]


def process_transcript_iter(transcript_words, window_size=10):
    # Look forwards
    for start, end, window_words in window_iter(transcript_words, window_size):
        subject_pos, subject = matching_word_list(window_words[0:1], subjects)
        if subject_pos is not None:
            keyword_pos, keyword = matching_word_list(window_words, keywords)
            if keyword_pos is not None:
                # A subject and keyword found, where the subject is to the left of the keyword
                yield subject, start + subject_pos, keyword, start + keyword_pos
            else:
                # Only a subject found
                yield subject, start + subject_pos, None, None
        else:
            # Look for keyword without a subject
            keyword_pos, keyword = matching_word_list(window_words[0:1], keywords)
            if keyword_pos is not None:
                subject_pos, subject = matching_word_list(window_words, subjects)
                if subject_pos is None:
                    yield None, None, keyword, start + keyword_pos
        # Now for a subject and keyword, where the subject is at the right-most end of the window (so the keyword is to the left)
        subject_pos, subject = matching_word_list(window_words[-1:], subjects)
        if subject_pos is not None:
            keyword_pos, keyword = matching_word_list(window_words, keywords)
            if keyword_pos is not None:
                # A subject and keyword found, where the subject is to the right of the keyword
                yield subject, start + subject_pos, keyword, start + keyword_pos


# Check if the file has a newline as the last character; if not, add it
def fix_newline(f):
    f_length = f.tell()
    f.seek(f_length-1, 0)
    lastchar = f.read(1)
    if lastchar != '\n':
        f.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--window', help='number of words that subject and keyword must be within (default = 10)', type=int,
                        default=10)
    parser.add_argument('--context', help='number of words before and after subject and keyword to extract (default = 20)', type=int,
                        default=20)
    parser.add_argument('--subjectfile', help='subject list file (default = subjects.csv)', type=argparse.FileType('r'),
                        default='subjects.csv')
    parser.add_argument('--keywordfile', help='keyword list file (default = keywords.csv)', type=argparse.FileType('r'),
                        default='keywords.csv')
    parser.add_argument('--normalizefile', help='normalize terms file (default = normalize_terms.csv)', type=argparse.FileType('r'),
                        default='normalize_terms.csv')
    parser.add_argument('--suppress-lone-subjects', action='store_true', help='do not write rows for subjects found but not co-located with keywords')
    parser.add_argument('--suppress-lone-keywords', action='store_true', help='do not write rows for keywords found but not co-located with subjects')
    parser.add_argument('transcript', help='filepath to transcript pdf or directory')

    args = parser.parse_args()

    # Read subjects, keywords, and normalize_terms
    with args.subjectfile as subjects_file:
        subjects_csv = csv.reader(subjects_file)
        for row in subjects_csv:
            subjects += [row[0]]
            subject_map[row[0]] = row[1]

    with args.keywordfile as keywords_file:
        keywords_csv = csv.reader(keywords_file)
        for row in keywords_csv:
            keywords += [row[0]]
            keyword_map[row[0]] = row[1]
            keyword_id[row[0]] = row[2]

    with args.normalizefile as normalize_terms_file:
        normalize_terms_csv = csv.reader(normalize_terms_file)
        for row in normalize_terms_csv:
            normalize_terms[row[0]] = row[1]

    pdfdocset = PDFTranscriptDocumentSet(args.transcript)

    # Start processing
    headers = ['extract_date', 'file', 'show_date', 'show_id', 'show_name', 'subject', 'subject_code', 'keyword', 'keyword_code', 'keyword_id', 'relevant?', 'extract']

    # If extracts.csv exists, append to it rather than overwriting it.
    if os.path.exists('extracts.csv'):
        append_extracts = True
        file_mode = 'a+'
    else:
        append_extracts = False
        file_mode = 'w'

    with open('extracts.csv', file_mode) as extract_file:
        # If the file was previously saved using Excel, it will be lacking a final \n character.
        # So, we need to check if it's missing; if so, add it so that appending starts on a new line.
        if append_extracts:
            fix_newline(extract_file)
        extract_csv = csv.writer(extract_file)
        if not append_extracts:
            extract_csv.writerow(headers)

        for pdfdoc in pdfdocset:
            show_info = pdfdoc.metadata

            m_transcript_filepath = show_info['show_file_path']
            print('Processing {}'.format(m_transcript_filepath))
            m_transcript_text = pdfdoc.text
            m_transcript_words = tokenize(m_transcript_text)
            for m_subject, m_subject_pos, m_keyword, m_keyword_pos in process_transcript_iter(m_transcript_words,
                                                                                              window_size=args.window):
                extract_date = datetime.datetime.now().strftime("%m/%d/%y %H:%M:%S")

                if m_keyword is None:
                    if not args.suppress_lone_subjects:
                        extract = ' '.join(
                            context(m_transcript_words, m_subject_pos,
                                    m_subject_pos,
                                    context_size=args.context))
                        extract_csv.writerow([extract_date,
                                              m_transcript_filepath,
                                              show_info['show_date'],
                                              show_info['show_id'],
                                              show_info['show_name'],
                                              m_subject,
                                              subject_map[m_subject],
                                              '',
                                              '',
                                              '',
                                              extract])
                elif m_subject is None:
                    if not args.suppress_lone_keywords:
                        extract = ' '.join(
                            context(m_transcript_words, m_keyword_pos,
                                    m_keyword_pos,
                                    context_size=args.context))

                        extract_csv.writerow([extract_date,
                                              m_transcript_filepath,
                                              show_info['show_date'],
                                              show_info['show_id'],
                                              show_info['show_name'],
                                              '',
                                              '',
                                              m_keyword,
                                              keyword_map[m_keyword],
                                              keyword_id[m_keyword],
                                              '',
                                              extract])
                else:
                    extract = ' '.join(
                        context(m_transcript_words, min(m_subject_pos, m_keyword_pos),
                                max(m_subject_pos, m_keyword_pos),
                                context_size=args.context))

                    extract_csv.writerow([extract_date,
                                          m_transcript_filepath,
                                          show_info['show_date'],
                                          show_info['show_id'],
                                          show_info['show_name'],
                                          m_subject,
                                          subject_map[m_subject],
                                          m_keyword,
                                          keyword_map[m_keyword],
                                          keyword_id[m_keyword],
                                          '',
                                          extract])