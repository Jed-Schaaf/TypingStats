import time as t, argparse as ap
from datetime import datetime as dt

def main():
    """TypingStats main program"""

    GOOD = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    parser = ap.ArgumentParser("TypingStats")
    parser.add_argument("--input", "-if",
                        help="Source file of text to use for typing test",
                        type=str, default="./test.txt")
    parser.add_argument("--output", "-of",
                        help="Statistics file to append typing results",
                        type=str, default="./results.txt")
    args = parser.parse_args()

    # get in/out files from user input (exec param or open-file dialog?)
    ifile = args.input
    ofile = args.output

    # set up statistics counters
    all_chars_count = good_chars_count = word_count = 0
    data = []

    with open(ifile,'r') as f:
        for line in f: # read file into memory to avoid counting disk I/O time
            data.append(line.rstrip('\r\n'))

    start = t.perf_counter_ns()  # start nanosecond timer
    for line in data:
        content_state = 'I'  # 'I'nitial, 'A'lpha/Numeric, 'B'lank/Punctuation

        # TODO: update input as user types

        text = input(line+'\n') # get user input
        for i in range(max(len(line), len(text))): # compare input line to file line
            x = line[i] if i < len(line) else ''
            y = text[i] if i < len(text) else ''

            # update word count
            if str.isalnum(x):
                if content_state != 'A': # new word
                    word_count += 1
                content_state = 'A'
            elif str.isspace(x) or not str.isprintable(x):
                if content_state != 'B': # new blank or punctuation
                    content_state = 'B'

            # update character counts
            if x == '' and y != '':
                print(WARN+y, end='')
                all_chars_count += 1
            elif x != '' and y == '':
                print(WARN+x, end='')
                all_chars_count += 1
            elif x != y: # show discrepancies
                print(FAIL+coalesce(y, x), end='')
                all_chars_count += 1
            elif x == y:
                print(GOOD+x, end='')
                all_chars_count += 1
                good_chars_count += 1

        # TODO: count edits to input line

        print(ENDC)
    duration = t.perf_counter_ns() - start # end nanosecond timer

    results = calculate_results(duration, all_chars_count, good_chars_count, word_count) # calculate results

    # display statistics
    print(f'duration: {duration/1_000_000_000:.1f} seconds')
    print(f'total characters: {all_chars_count}')
    print(f'correct characters: {good_chars_count}')
    print(f'accuracy: {results[0]:.1%}')
    print(f'keys per second: {results[1]:.2f}')
    print(f'words per minute: {results[2]:.2f}')

    # save results for historical comparison
    with open(ofile, 'a') as fo:
        newline = '\n'
        fo.write(str(dt.now())+newline)
        fo.write(ifile+newline)
        fo.write(f'{duration}, {all_chars_count}, {good_chars_count}, {word_count}')
        fo.write(newline+newline)

    # end program
    # TODO: ask for repeat?


def calculate_results(duration, all_chars, good_chars, words):
    """determine keys-per-second, words-per-minute, accuracy, and other results"""
    accuracy = float(good_chars) / float(all_chars)
    kps = all_chars / (duration / 1_000_000_000)
    wpm = words / (duration / 60_000_000_000)
    return accuracy, kps, wpm


def coalesce(*args):
    """get first non-None item from list of arguments"""
    for arg in args:
        if arg is not None:
            return arg
    return None

main()
