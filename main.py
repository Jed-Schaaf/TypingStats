import time as t, argparse as ap, readchar as rc, platform as pf
from datetime import datetime as dt
from enum import Enum

class PState(Enum):
    GOOD = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    def __add__(self, other):
        return str(self.value)+str(other)
    def __str__(self):
        return str(self.value)

class CState(Enum):
    INITIAL = 0
    ALPHANUM = 1
    BLANKPUNCT = 2


def main():
    """TypingStats main program"""

    if pf.system() == 'Linux':
        char_backspace = '\x7f'
        word_backspace = '\x08'
    else:
        char_backspace = '\x08'
        word_backspace = '\x7f'

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
    all_chars_count = typed_keys = word_count = 0
    data = []
    correct = []

    with open(ifile,'r') as f:
        for line in f: # read file into memory to avoid counting disk I/O time
            data.append(line.rstrip('\r\n'))

    start = t.perf_counter_ns() # start nanosecond timer
    first = True
    abort = False
    for line in data:
        content_state:CState = CState.INITIAL

        print(line)
        text = []
        x, ctrl = readkbd() # wait for next keyboard input
        typed_keys += 1

        # reset start time in case user doesn't start typing immediately
        if first:
            first = False
            start = t.perf_counter_ns()

        while x != rc.key.ENTER:

            if x == char_backspace: # backtrack state
                if text:
                    x = text.pop()
                    all_chars_count -= 1
                    correct.pop()
                else:
                    x = ''
                if x != '':
                    if content_state == CState.ALPHANUM:
                        print(PState.ENDC+'\b \b', end='')
                        if str.isalnum(x):
                            pass
                        elif str.isspace(x) or not str.isprintable(x):
                            content_state = CState.BLANKPUNCT
                            word_count -= 1
                    elif content_state == CState.BLANKPUNCT:
                        print(PState.ENDC+'\b \b', end='')
                        if str.isalnum(x):
                            content_state = CState.ALPHANUM
                    elif content_state == CState.INITIAL:
                        pass
                if not text:
                    content_state = CState.INITIAL

            elif x == word_backspace:
                if content_state == CState.ALPHANUM:
                    counter = 0
                    while text:
                        x = text[-1]
                        if str.isalnum(x):
                            text.pop()
                            all_chars_count -= 1
                            correct.pop()
                            counter += 1
                        else:
                            content_state = CState.BLANKPUNCT
                            break
                    print(PState.ENDC+'\b'*counter+' '*counter+'\b'*counter, end='')
                    if not text:
                        content_state = CState.INITIAL
                    word_count -= 1
                elif content_state == CState.BLANKPUNCT:
                    counter = 0
                    while text:
                        x = text[-1]
                        if str.isalnum(x):
                            content_state = CState.ALPHANUM
                            break
                        else:
                            text.pop()
                            all_chars_count -= 1
                            correct.pop()
                            counter += 1
                    print(PState.ENDC+'\b'*counter+' '*counter+'\b'*counter, end='')
                    if not text:
                        content_state = CState.INITIAL
                elif content_state == CState.INITIAL:
                    pass

            elif str.isprintable(x):
                text.append(x)
                y = line[len(text) - 1] if len(text) <= len(line) else ''

                # update word count
                if str.isalnum(x):
                    if content_state != CState.ALPHANUM: # new word
                        word_count += 1
                    content_state = CState.ALPHANUM
                elif str.isspace(x):
                    if content_state != CState.BLANKPUNCT: # new blank or punctuation
                        content_state = CState.BLANKPUNCT

                # update character counts
                if x == '' and y != '':
                    print(PState.WARN+y, end='')
                    all_chars_count += 1
                    correct.append(False)
                elif x != '' and y == '':
                    print(PState.WARN+x, end='')
                    all_chars_count += 1
                    correct.append(False)
                elif x != y: # show discrepancies
                    print(PState.FAIL+x, end='')
                    all_chars_count += 1
                    correct.append(False)
                elif x == y:
                    print(PState.GOOD+x, end='')
                    all_chars_count += 1
                    correct.append(True)

            elif x == rc.key.CTRL_C:
                abort = True # interrupt test and get current results
                break

            else:
                pass # ignore invalid input
                #print(repr(x)) #show me what was typed

            x, ctrl = readkbd()
            typed_keys += 1

        if abort:
            print(PState.ENDC)
            break

        if len(text) < len(line):
            for m in range(len(text), len(line)):
                print(PState.WARN+line[m], end='')
                all_chars_count += 1

        print(PState.ENDC)
    duration = t.perf_counter_ns() - start # end nanosecond timer

    good = sum(correct)
    results = calculate_results(duration, all_chars_count, typed_keys, good, word_count) # calculate results

    # display statistics
    print(f'duration: {duration/1_000_000_000:.1f} seconds')
    print(f'total characters: {all_chars_count}')
    print(f'correct characters: {good}')
    print(f'accuracy: {results[0]:.1%}')
    print(f'keys per second: {results[1]:.2f}')
    print(f'words per minute: {results[2]:.2f}')

    # save results for historical comparison
    with open(ofile, 'a') as fo:
        newline = '\n'
        fo.write(str(dt.now())+newline)
        fo.write(ifile+newline)
        fo.write(f'{duration}, {all_chars_count}, {good}, {word_count}')
        fo.write(newline+newline)

    # end program
    # TODO: ask for repeat?


def readkbd():
    """read the next character or control character from the keyboard"""
    retval = rc.readchar()
    control = False
    if retval == '\000' or retval == '\xe0':
        control = True
        retval = rc.readchar()
    return retval, control


def calculate_results(duration, all_chars, typed_keys, good_chars, words):
    """determine keys-per-second, words-per-minute, accuracy, and other results"""
    accuracy = float(good_chars) / float(all_chars)
    kps = typed_keys / (duration / 1_000_000_000)
    wpm = words / (duration / 60_000_000_000)
    return accuracy, kps, wpm


if __name__ == '__main__':
    main()

