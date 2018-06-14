import collections
from .helpers import makeInverse, makeInverseVal
from .locality import Locality
from .text import Text
from .search.search import Search


class OtypeFeature(object):
  def __init__(self, api, data=None):
    self.api = api
    self.data = data
    self.slotType = self.data[-2]
    self.maxSlot = self.data[-1]
    self.maxNode = len(self.data) - 2 + self.maxSlot

  def v(self, n):
    if n == 0:
      return None
    if n < self.maxSlot + 1:
      return self.data[-2]
    m = n - self.maxSlot
    if m <= len(self.data) - 2:
      return self.data[m - 1]
    return None

  def s(self, val):
    # NB: the support attribute has been added by precomputing __levels__
    if val in self.support:
      (b, e) = self.support[val]
      return range(b, e + 1)
    else:
      return ()

  def sInterval(self, val):
    # NB: the support attribute has been added by precomputing __levels__
    if val in self.support:
      return self.support[val]
    else:
      return ()


class OslotsFeature(object):
  def __init__(self, api, data=None):
    self.api = api
    self.data = data
    self.maxSlot = self.data[-1]

  def s(self, n):
    if n == 0:
      return ()
    if n < self.maxSlot + 1:
      return (n, )
    m = n - self.maxSlot
    if m <= len(self.data) - 1:
      return self.data[m - 1]
    return ()


class NodeFeature(object):
  def __init__(self, api, data):
    self.api = api
    self.data = data

  def v(self, n):
    if n in self.data:
      return self.data[n]
    return None

  def s(self, val):
    Crank = self.api.C.rank.data
    return tuple(
        sorted(
            [n for n in self.data if self.data[n] == val],
            key=lambda n: Crank[n - 1],
        )
    )

  def freqList(self, nodeTypes=None):
    fql = collections.Counter()
    if nodeTypes is None:
      for n in self.data:
        fql[self.data[n]] += 1
    else:
      otype = self.api.F.otype.v
      for n in self.data:
        if otype(n) in nodeTypes:
          fql[self.data[n]] += 1
    return tuple(sorted(fql.items(), key=lambda x: (-x[1], x[0])))


class EdgeFeature(object):
  def __init__(self, api, data, doValues):
    self.api = api
    self.doValues = doValues
    if type(data) is tuple:
      self.data = data[0]
      self.dataInv = data[1]
    else:
      self.data = data
      self.dataInv = makeInverseVal(self.data) if doValues else makeInverse(self.data)

  def f(self, n):
    Crank = self.api.C.rank.data
    if n in self.data:
      if self.doValues:
        return tuple(sorted(
            self.data[n].items(),
            key=lambda mv: Crank[mv[0] - 1],
        ))
      else:
        return tuple(sorted(
            self.data[n],
            key=lambda m: Crank[m - 1],
        ))
    return ()

  def t(self, n):
    Crank = self.api.C.rank.data
    if n in self.dataInv:
      if self.doValues:
        return tuple(sorted(
            self.dataInv[n].items(),
            key=lambda mv: Crank[mv[0] - 1],
        ))
      else:
        return tuple(sorted(
            self.dataInv[n],
            key=lambda m: Crank[m - 1],
        ))
    return ()

  def freqList(self, nodeTypesFrom=None, nodeTypesTo=None):
    if nodeTypesFrom is None and nodeTypesTo is None:
      if self.doValues:
        fql = collections.Counter()
        for (n, vals) in self.data.items():
          for val in vals.values():
            fql[val] += 1
        return tuple(sorted(fql.items(), key=lambda x: (-x[1], x[0])))
      else:
        fql = 0
        for (n, ms) in self.data.items():
          fql += len(ms)
        return fql
    else:
      otype = self.api.F.otype.v
      if self.doValues:
        fql = collections.Counter()
        for (n, vals) in self.data.items():
          if nodeTypesFrom is None or otype(n) in nodeTypesFrom:
            for (m, val) in vals.items():
              if nodeTypesTo is None or otype(m) in nodeTypesTo:
                fql[val] += 1
        return tuple(sorted(fql.items(), key=lambda x: (-x[1], x[0])))
      else:
        fql = 0
        for (n, ms) in self.data.items():
          if nodeTypesFrom is None or otype(n) in nodeTypesFrom:
            for m in ms:
              if nodeTypesTo is None or otype(m) in nodeTypesTo:
                fql += len(ms)
        return fql


class Computed(object):
  def __init__(self, api, data):
    self.api = api
    self.data = data


class NodeFeatures(object):
  pass


class EdgeFeatures(object):
  pass


class Computeds(object):
  pass


class Api(object):
  def __init__(self, TF):
    self.TF = TF
    self.ignored = tuple(sorted(TF.featuresIgnored))
    self.F = NodeFeatures()
    self.Feature = self.F
    self.E = EdgeFeatures()
    self.Edge = self.E
    self.C = Computeds()
    self.Computed = self.C
    self.info = TF.tm.info
    self.error = TF.tm.error
    self.cache = TF.tm.cache
    self.reset = TF.tm.reset
    self.indent = TF.tm.indent
    self.loadLog = TF.tm.cache
    setattr(self, 'FeatureString', self.Fs)
    setattr(self, 'EdgeString', self.Es)
    setattr(self, 'ComputedString', self.Cs)
    setattr(self, 'Nodes', self.N)
    setattr(self, 'AllFeatures', self.Fall)
    setattr(self, 'AllEdges', self.Eall)
    setattr(self, 'AllComputeds', self.Call)

  def Fs(self, fName):
    if not hasattr(self.F, fName):
      self.error('Node feature "{}" not loaded'.format(fName))
      return None
    return getattr(self.F, fName)

  def Es(self, fName):
    if not hasattr(self.E, fName):
      self.error('Edge feature "{}" not loaded'.format(fName))
      return None
    return getattr(self.E, fName)

  def Cs(self, fName):
    if not hasattr(self.C, fName):
      self.error('Computed feature "{}" not loaded'.format(fName))
      return None
    return getattr(self.C, fName)

  def N(self):
    for n in self.C.order.data:
      yield n

  def sortNodes(self, nodeSet):
    Crank = self.C.rank.data
    return sorted(nodeSet, key=lambda n: Crank[n - 1])

  def Fall(self):
    return sorted(x[0] for x in self.F.__dict__.items())

  def Eall(self):
    return sorted(x[0] for x in self.E.__dict__.items())

  def Call(self):
    return sorted(x[0] for x in self.C.__dict__.items())

  def makeAvailableIn(self, scope):
    for member in dir(self):
      if '_' not in member and member != 'makeAvailableIn':
        scope[member] = getattr(self, member)

  def ensureLoaded(self, features):
    F = self.F
    E = self.E
    TF = self.TF
    info = self.info

    needToLoad = set()
    loadedFeatures = set()
    for fName in sorted(features):
      fObj = TF.features.get(fName, None)
      if not fObj:
        info(f'Cannot load feature "{fName}": not in dataset')
        continue
      if fObj.dataLoaded and (hasattr(F, fName) or hasattr(E, fName)):
        loadedFeatures.add(fName)
      else:
        needToLoad.add(fName)
    if len(needToLoad):
      TF.load(
          needToLoad,
          add=True,
          silent=True,
      )
      loadedFeatures |= needToLoad
    return loadedFeatures


def addSortKey(api):
  Crank = api.C.rank.data
  api.sortKey = lambda n: Crank[n - 1]


def addOtype(api):
  setattr(api.F.otype, 'all', tuple(o[0] for o in api.C.levels.data))
  setattr(api.F.otype, 'support', dict(((o[0], (o[2], o[3])) for o in api.C.levels.data)))


def addLocality(api):
  api.L = Locality(api)
  api.Locality = api.L


def addText(api):
  api.T = Text(api)
  api.Text = api.T


def addSearch(api, silent):
  api.S = Search(api, silent)
  api.Search = api.S
