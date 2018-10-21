#!/usr/bin/env python
import testarium, testarium.score.fafr
import random, json, time


@testarium.experiment.set_run
def MyRun(commit):
    c = commit.config
    dir = commit.dir
    pos = open(dir + '/pos.txt', 'w')
    neg = open(dir + '/neg.txt', 'w')
    for i in xrange(100): pos.write(str(random.random()) + '\n')
    for i in xrange(100): neg.write(str(random.random()) + '\n')
    return 0


@testarium.experiment.set_score
def MyScore(commit):
    d = testarium.score.fafr.Score(commit.dir)
    d['test'] = 1
    return d


@testarium.testarium.set_print
def MyPrint(commit):
    try:
        a = str(commit.config['a'])
    except:
        a = ''

    score = str(commit.desc['score'])
    return ['name', 'a', 'score', 'config'], [commit.name, a, score, 'file://storage/.testarium/' +
                                              commit.desc['branch'] + '/' + commit.name + '/config.json']


@testarium.testarium.set_compare
def MyCompare(self, other):
    if self._init:
        if self.desc['score'] > other.desc['score']:
            return -1;
        elif self.desc['score'] < other.desc['score']:
            return 1;
        else:
            return 0
    else:
        return -1


if __name__ == '__main__':
    testarium.testarium.best_score_is_min()
    testarium.main()
