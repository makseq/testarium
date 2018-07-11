#!/usr/bin/env python
'''
Testarium
Copyright (C) 2014 Danila Doroshin, Maxim Tkachenko, Alexander Yamshinin

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
import json
import numpy as np
import threading
from multiprocessing import Process, Queue
from multiprocessing.pool import ThreadPool
from functools import partial

threadLocal = threading.local()


def get_pos_neg(model, test, model_labels, test_labels, verbose=False, metric='cos'):
    """ Calculate positive and negative scores by vectors (dvectors, ivectors, embeddings)
    
    :param model: model vectors (enroll)
    :param test: test vectors (eval), if it's the same to model it will be upper triangle matrix taken for positives
    :param model_labels: model labels 
    :param test_labels: test labels 
    :param verbose: print info flag
    :param metric: 'cos' or 'hamming' 
    :return: positive and negative scores
    """
    pos, neg = [], []
    model_eq_test = id(model) == id(test)  # check if model is the same as test

    # calculate hamming distances
    if isinstance(metric, basestring):
        if metric == 'hamming':
            model = model > 0
            test = test > 0
            def hamming_distance(A, B):
                import scipy.spatial.distance
                scores = np.zeros((A.shape[0], B.shape[0]), dtype=np.int)
                pool = ThreadPool()
                def task(i):
                    out = getattr(threadLocal, 'out', None)
                    if out is None:
                        out = np.zeros(A.shape).astype(np.bool)
                        setattr(threadLocal, 'out', out)
                    a = A[i]
                    scores[i] = -np.count_nonzero(np.not_equal(a[np.newaxis, :], B, out=out), axis=-1)
                pool.map(task, range(A.shape[0]))
                pool.close()
                return scores
            m = hamming_distance
        # calculate cos distances
        elif metric == 'cos':
            m = partial(lambda A, B: np.dot(A, B.T))
        # incorrect distance
        else:
            raise Exception('Incorrect distance metric')
    elif callable(metric):
        m = metric
    else:
        raise Exception('Incorrect metric')

    scores = m(model, test)

    for i, s in enumerate(model_labels):
        js = test_labels == s  # positives
        not_js = np.logical_not(js)  # negatives

        # take only upper triangle of matrix for positives if model == test
        if model_eq_test:
            js[0: i+1] = False
            not_js[0: i] = False

        if np.sum(js) > 0:
            pos += [scores[i, js]]
        if np.sum(not_js) > 0:
            neg += [scores[i, not_js]]

    pos, neg = np.hstack(pos), np.hstack(neg)

    if verbose:
        print('Positives number: %i' % len(pos))
        print('Negatives number: %i' % len(neg))

    return pos, neg


def fafr_parallel(pos, neg, N, prcount):
    FA = np.zeros((N + 1,))
    FR = np.zeros((N + 1,))
    Thresh = np.zeros((N + 1,))

    indexes = [range(N + 1)[m::prcount] for m in xrange(prcount)]
    out_q = Queue()
    prs = []
    for j in xrange(prcount):
        p = threading.Thread(target=fafr_process, args=(pos, neg, N, indexes[j], j, out_q))
        p.start()
        prs.append(p)

    fins = 0
    while fins < prcount:
        FA_id, FR_id, Thresh_id, id = out_q.get(True)
        fins += 1
        FA[indexes[id]] = FA_id
        FR[indexes[id]] = FR_id
        Thresh[indexes[id]] = Thresh_id

    for p in prs:
        p.join()

    return FA, FR, Thresh


def fafr_process(pos, neg, N, inds, pid, outq):
    psize = pos.shape[0]
    nsize = neg.shape[0]
    lb = np.min([np.min(pos), np.min(neg)])
    ub = np.max([np.max(pos), np.max(neg)])
    prec = (ub - lb) / float(N)

    cnt = len(inds)
    FA = np.zeros((cnt,))
    FR = np.zeros((cnt,))
    Thresh = np.zeros((cnt,))
    for id, n in enumerate(inds):
        a = lb + n * prec

        FP = np.count_nonzero(neg[neg > a])
        FN = np.count_nonzero(pos[pos <= a])

        FA[id] = float(FP) / nsize
        FR[id] = float(FN) / psize
        Thresh[id] = a

    outq.put((FA, FR, Thresh, pid))


def fafr(pos, neg, step_size=1000.0):
    # computes false alarms, rejects and corresponding thresholds for a given
    # target and background data
    # INPUTS
    # pos :              target data (where label = +1)
    # neg :              background data  (where label = -1)
    # OUTPUTS
    # FA:               false alarms distribution along thresholds
    # FR:               false rejects distribution along thresholds
    # Thresh             thresholds

    pos = np.array(pos) if isinstance(pos, list) else pos
    neg = np.array(neg) if isinstance(neg, list) else neg

    psize = float(pos.shape[0])
    if psize == 0: psize = 1.0
    nsize = float(neg.shape[0])
    if nsize == 0: nsize = 1.0

    con_neg = np.linspace(np.min(neg), np.max(neg), step_size)
    con_pos = np.linspace(np.min(pos), np.max(pos), step_size)
    con = np.concatenate((con_neg, con_pos))
    con = np.sort(con)
    #step = con.shape[0]/200 if len(con) > 200 else 1
    #con = s[::step]
    #if con[-1] != s[-1]:
    #    con = np.concatenate([con, [s[-1]]])

    FA = []
    FR = []
    Thresh = []
    prevFP = 0
    prevFA = 0
    first = True

    for a in con:
        FP = np.count_nonzero(neg[neg > a])
        FN = np.count_nonzero(pos[pos <= a])
        
        if first:
            prevFP = FP
            prevFN = FN
            FA.append(float(FP) / (nsize))
            FR.append(float(FN) / (psize))
            Thresh.append(a)
            first = False

        if prevFP != FP or prevFN != FN:
            FA.append(float(FP) / (nsize))
            FR.append(float(FN) / (psize))
            Thresh.append(a)

        prevFP = FP
        prevFN = FN

    return np.array(FA), np.array(FR), np.array(Thresh)


def ScorePosNeg(pos, neg):
    FA, FR, th = fafr(np.array(pos), np.array(neg))
    data = {'fa': FA, 'fr': FR, 't': th}

    # calc EER
    eer = FA[np.argmin(np.abs(FA - FR))]
    minDCF = np.min(100 * FA + FR)
    return {'score': eer, 'minDCF': minDCF, 'graph': data}
    
        
def ScoreDirectory(dir):
    # load pos and neg
    pos = dir + '/pos.txt'
    neg = dir + '/neg.txt'
    try:
        pos = np.loadtxt(pos)
        neg = np.loadtxt(neg)
    except:
        print 'Score: Error: No pos or neg file';
        return -1
    pos = pos[np.logical_not(np.isnan(pos))]
    neg = neg[np.logical_not(np.isnan(neg))]

    # calc fafr
    FA, FR, th = fafr(pos, neg)

    # save cache
    data = [{'x': FA[i], 'y': FR[i], 't': th[i]} for i, x in enumerate(FR)]

    tmp = json.encoder.FLOAT_REPR
    json.encoder.FLOAT_REPR = lambda o: format(o, '.6f')
    j = json.dumps({'xAxis': 'False Alarm', 'yAxis': 'False Reject', 'data': data})
    json.encoder.FLOAT_REPR = tmp
    try:
        open(dir + '/fafr.txt', 'w').write(j)
    except:
        print "Can't save: " + dir + '/fafr.txt'

    # calc EER
    eer = FA[np.argmin(np.abs(FA - FR))]
    minDCF = np.min(100 * FA + FR)
    return {'score': eer, 'minDCF': minDCF}


def fafr_cache(pos, neg, fname, commit):
    print 'FAFR: Positive and negative scores count:', len(pos), len(neg)
    pos, neg = np.array(pos), np.array(neg)
    FA, FR, th = fafr(pos, neg)

    # save cache
    data = [{'x': FA[i], 'y': FR[i], 't': th[i]} for i, x in enumerate(FR)]
    j = json.dumps({'xAxis': 'False Alarm', 'yAxis': 'False Reject', 'data': data})
    try: open(commit.dir + '/' + fname, 'w').write(j)
    except: print "Can't save: " + commit.dir + '/' + fname

    # calc EER
    eer = FA[np.argmin(np.abs(FA - FR))]
    minDCF = np.min(100 * FA + FR)
    return eer, minDCF


def ScoreCommit(commit):
    all = commit.meta.GetAllIds()
    probs_keys = commit.meta.GetMeta(all[0])['probs'].keys()
    common_pos, common_neg = [], []

    results = {}
    for name in probs_keys:  # unpack probs by name
        pos, neg = [], []
        for _id in commit.meta.GetAllIds():  # collect data from commit meta and file db
            probs = commit.meta.GetMeta(_id)['probs']
            targets = commit.filedb.GetFile(_id)['targets']

            if name in targets and targets[name] == 1:
                pos += [probs[name]]
            else:
                neg += [probs[name]]

        open(commit.dir + '/pos.'+name+'.txt', 'w').write('\n'.join([str(i) for i in pos]))
        open(commit.dir + '/neg.'+name+'.txt', 'w').write('\n'.join([str(i) for i in neg]))

        eer, minDCF = fafr_cache(pos, neg, 'fafr.' + name + '.txt', commit)
        results.update({name: {'eer': eer, 'minDCF': minDCF, 'pos_number': len(pos), 'neg_number': len(neg)}})

        common_pos += pos
        common_neg += neg
        open(commit.dir + '/pos.common.txt', 'w').write('\n'.join([str(i) for i in common_pos]))
        open(commit.dir + '/neg.common.txt', 'w').write('\n'.join([str(i) for i in common_neg]))



    eer, minDCF = fafr_cache(common_pos, common_neg, 'fafr.txt', commit)
    return {'score': eer, 'minDCF': minDCF, 'fafr.targets': results, 'pos_number': len(common_pos), 'neg_number': len(common_neg)}

    
def Score(o):
    if isinstance(o, str) or isinstance(o, unicode):
        return ScoreDirectory(o)
    elif isinstance(o, list) and len(o) == 2:
        return ScorePosNeg(o[0], o[1])
    else:
        return ScoreCommit(o)

