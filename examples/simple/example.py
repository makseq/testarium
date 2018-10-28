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
    [pos.write(str(random.random() * c['a']) + '\n') for _ in xrange(100)]
    [neg.write(str(random.random() * c['a']) + '\n') for _ in xrange(100)]

    # pos.close()
    # neg.close()
    raw_input('press enter')
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


@testarium.testarium.set_compare
def my_compare(self, other):
    if self._init:
        if self.desc['score'] > other.desc['score']:
            return -1
        elif self.desc['score'] < other.desc['score']:
            return 1
        else:
            return 0
    else:
        return -1


if __name__ == '__main__':
    testarium.testarium.best_score_is_max()
    testarium.main()
