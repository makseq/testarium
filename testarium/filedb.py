import os, json, random
from utils import *

class FileDataBaseException(Exception): pass

class FileDataBase:
    def __init__(self):
        self.files = {}
        self.meta = {}
        self.last_id = 0
        self.shuffled_keys = None
        self.shuffled_last = 0
        self._init = False
        self._files_saved = False

    def IsInitialized(self):
        return self._init

    def ScanDirectoryRecursively(self, watch_dir, extension):
        count = 0
        exist = 0

        files_ok = {}
        for root, _, files in os.walk(watch_dir):
            for filename in files:
                if filename.endswith(extension):
                    _id = str(self.last_id)
                    path = root + '/' + filename

                    # find duplicates
                    value = { 'path': path }
                    added = False
                    for i in self.files:
                        if self.files[i]['path'] == value['path']:
                            files_ok[i] = value
                            added = True
                            exist += 1
                            break

                    if not added:
                        files_ok[_id] = value
                        self.last_id += 1
                        count += 1


        self.files = files_ok
        self._init = True
        self._files_saved = False if count > 0 else True
        return count, exist

    def ShuffleFiles(self):
        self.shuffled_keys = self.files.keys()
        myRandom = random.Random(42)
        myRandom.shuffle(self.shuffled_keys)

    def GetFilesPortion(self, count, count_is_percent=True):
        if self.shuffled_keys is None:
            raise FileDataBaseException('Use ShuffleFiles before GetFilesPortion')

        if count_is_percent:
            count *= self.GetFilesNumber()

        start = self.shuffled_last
        end = None if count is None else int(self.shuffled_last+count)
        self.shuffled_last = end
        return self.shuffled_keys[start:end]

    def GetFile(self, _id):
        return self.files[_id]

    def GetPath(self, _id):
        return self.files[_id]['path']

    def SetMeta(self, _id, data):
        if not isinstance(data, dict):  raise FileDataBaseException('data must be a dict '+str(data))
        if not _id in self.files: raise FileDataBaseException('no such _id '+str(_id))
        self.meta[_id] = data

    def AddMeta(self, _id, data):
        if not isinstance(data, dict):  raise FileDataBaseException('data must be a dict '+str(data))
        if not _id in self.files: raise FileDataBaseException('no such _id '+str(_id))
        if _id in self.meta: self.meta[_id].update(data)
        else: self.meta[_id] = data

    def SetFiles(self, other_filedb):
        self.files = other_filedb.files
        self._init = other_filedb._init
        self._files_saved = other_filedb._files_saved

    def GetFiles(self):
        return self.files

    def GetFilesNumber(self):
        return len(self.files)

    def SaveFiles(self, filename):
        if not self._files_saved:
            try:
                json.dump(self.files, open(filename, 'w'))
                self._files_saved = True
                log('FileDB saved to ', filename)
                return True
            except: return False
        else:
            return False

    def LoadFiles(self, filename):
        try:
            self._init = False
            self._files_saved = False
            self.files = json.load(open(filename))
            self.last_id = max([int(i) for i in self.files.keys()])
            self._init = True
            self._files_saved = True
        except: return False
        return True

    def SaveMeta(self, filename):
        # save json with meta info
        tmp = json.encoder.FLOAT_REPR
        json.encoder.FLOAT_REPR = lambda o: format(o, '.2f')
        try: json.dump(self.meta, open(filename, 'w'), sort_keys=True)
        except: return False
        json.encoder.FLOAT_REPR = tmp
        return True

    def LoadMeta(self, filename):
        try: self.meta = json.load(open(filename))
        except: return False
        return True