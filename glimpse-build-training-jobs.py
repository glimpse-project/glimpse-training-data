#!/usr/bin/env python

import argparse
import json
import copy
import datetime


def linspace(min, max, n_values):
    step = (max - min) / (int(n_values) - 1)
    i = 0
    while i < n_values - 1:
        yield min
        min += step
        i += 1
    yield max


def parse_value(string):
    if string.lower() == 'true':
        return True
    elif string.lower() == 'false':
        return False
    else:
        try:
            if '.' in string:
                return float(string)
            else:
                return int(string)
        except ValueError:
            return string


def parse_param(string):
    params = string.split(',')
    if len(params) != 2:
        msg = '%r has an incorrect number of parameters, expected 2' % string
        raise argparse.ArgumentTypeError(msg)
    return (params[0], [parse_value(params[1])])


def parse_list(string):
    params = string.split(',')
    if len(params) < 3:
        msg = '%r does not have at least two values' % string
        raise argparse.ArgumentTypeError(msg)
    return (params[0], map(lambda x: parse_value(x), params[1:]))


def parse_range(string):
    params = string.split(',')
    if len(params) != 4:
        msg = ('%r has an incorrect number of parameters, expected 4 comma '
               'separted values like: <name>,<min>,<max>,<N-steps>' % string)
        raise argparse.ArgumentTypeError(msg)

    min = parse_value(params[1])
    max = parse_value(params[2])

    n_values = int(params[3])
    if n_values < 2:
        msg = '%r specifies less than 2 values' % string
        raise argparse.ArgumentTypeError(msg)

    min_type = type(min)
    max_type = type(max)
    if (min_type != int and min_type != float) or \
       (max_type != int and max_type != float):
        msg = '%r has incorrect types for min or max values, expected numbers' % string
        raise argparse.ArgumentTypeError(msg)

    return (params[0], list(linspace(min, max, n_values)))


parser = argparse.ArgumentParser(
    description='Generate job files for train_rdt',
    epilog='Example usage: %(prog)s --template training-job-templates/iphone-x-training.json --param-list index,tree0,tree1,tree2')

parser.add_argument('-t', '--template',
                    help='A template job description with default values')
parser.add_argument('-s', '--param-set', action='append',
                    default=[], type=parse_param,
                    help='Set a named parameter')
parser.add_argument('-l', '--param-list', action='append',
                    default=[], type=parse_list,
                    help='Vary a named parameter with these specific values')
parser.add_argument('-r', '--param-range', action='append',
                    default=[], type=parse_range,
                    help='Vary a given parameter over a range, described with '
                         'four comma separated components: '
                         '<name>,<min>,<max><N-steps> '
                         '(e.g. --param-rage example_prop,0.1,0.9,10)')

args = parser.parse_args()

# After the parsing that's done by the custom parsers given for these arguments
# we will end up with a props array like:
#
#   [(prop0, [val0, val1, val2]), (prop1, [val0, val1])]
#
props = args.param_set + args.param_list + args.param_range
job_id = 0

dt = datetime.datetime.today()
date_str = "%04u-%02u-%02u" % (dt.year, dt.month, dt.day)


def expand_vars(job, value):
    return value.format(
        job=job_id,
        index=job['index'],
        date=date_str)


def build_jobs_recursive(job, prop_index=0):
    global job_id
    jobs = []

    if prop_index >= len(props):
        job['index'] = expand_vars(job, job['index'])
        job['out_file'] = expand_vars(job, job['out_file'])
        job_id += 1
        return [job]

    prop = props[prop_index]
    for val in prop[1]:
        job[prop[0]] = val
        jobs += build_jobs_recursive(copy.deepcopy(job), prop_index + 1)

    return jobs


if args.template:
    with open(args.template, 'r') as fp:
        job_template = json.load(fp)
else:
    job_template = {}

jobs = build_jobs_recursive(copy.deepcopy(job_template))
print(json.dumps(jobs, indent=2))
