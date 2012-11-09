from subprocess import *
import re
import sys

def scrape_help(cmd_name):

    cmd = "COLUMNS=1000 conda %s -h" % cmd_name

    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)

    output = p.stdout.read()

    # groups:                ----1---- -----2----
    usage_pat = re.compile(r'(^usage): (conda .*)\n')
    usage = usage_pat.search(output)

    # groups:                          --1-
    desc_pat = re.compile(r'usage.*\n\n(.*)\n\n')
    desc = desc_pat.search(output)

    # groups:                                               --1--   --2-
    positional_pat = re.compile(r'positional arguments:\n\s+(\w*)\s+(.*)\n')
    pos = positional_pat.search(output)

    # groups:                            ---1--
    optional_pat = re.compile(r'(optional(.*\n)*)$')
    opt = optional_pat.search(output)
    options = opt.group(1)

    yn_pat = re.compile(r'{.*}')

    options = yn_pat.sub('', options)


    output = desc.group(1)

    output += "\n\n**%s** ``%s``\n\n" % (usage.group(1), usage.group(2))

    if pos:
        output += "*%s*\n\t%s\n\n" % (pos.group(1), pos.group(2))

    output += options

    print output

if __name__ == '__main__':
    scrape_help(sys.argv[1])