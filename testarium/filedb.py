import os, json

class FileDataBaseException(Exception): pass

class FileDataBase:
    def __init__(self):
        self.files = {}
        self.meta = {}
        self.last_id = 0

    def ScanDirectoryRecursively(self, watch_dir, extension):
        for root, _, files in os.walk(watch_dir):
            for filename in files:
                if filename.endswith(extension):
                    id = str(self.last_id)
                    self.last_id += 1
                    path = root + '/' + filename
                    self.files[id] = { 'path': path, 'size': os.path.getsize(path) }

    def SetMeta(self, id, data):
        if not isinstance(data, dict):  raise FileDataBaseException('data must be a dict '+str(data))
        if not id in self.files: raise FileDataBaseException('no such id '+str(id))
        self.meta[id] = data

    def AddMeta(self, id, data):
        if not isinstance(data, dict):  raise FileDataBaseException('data must be a dict '+str(data))
        if not id in self.files: raise FileDataBaseException('no such id '+str(id))
        if id in self.meta: self.meta[id].update(data)
        else: self.meta[id] = data

    def SetFiles(self, files):
        self.files = files

    def GetFiles(self):
        return self.files

    def SaveFiles(self, filename):
        try: json.dump(self.files, open(filename, 'w'), sort_keys=True)
        except: return False
        return True

    def LoadFiles(self, filename):
        try: self.files = json.load(open(filename))
        except: return False
        return True

    def SaveMeta(self, filename):
        try: json.dump(self.meta, open(filename, 'w'), sort_keys=True)
        except: return False
        return True

    def LoadMeta(self, filename):
        try: self.meta = json.load(open(filename))
        except: return False
        return True