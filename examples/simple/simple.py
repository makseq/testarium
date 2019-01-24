#!/usr/bin/env python
import random
import testarium
import testarium.score.fafr


@testarium.experiment.set_run
def my_run(commit):
    # prepare
    d = commit.dir
    c = commit.config

    # run experiment
    pos = open(d + '/pos.txt', 'w')
    neg = open(d + '/neg.txt', 'w')
    [pos.write(str(random.random() * c['a']) + '\n') for _ in range(100)]
    [neg.write(str(random.random() * c['a']) + '\n') for _ in range(100)]
    return 0


@testarium.experiment.set_score
def my_score(commit):
    d = testarium.score.fafr.Score(commit.dir)
    d['test.param'] = 1
    return d


@testarium.testarium.set_print
def my_print(commit):
    score = '%0.2f' % (commit.desc['score'] * 100.0)

    return ['name', 'a', 'test', 'score'], \
           [commit.name, commit.config['a'], commit.desc['test.param'], score]

if __name__ == '__main__':
    testarium.testarium.best_score_is_max()
    testarium.main()
