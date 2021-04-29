# Author: Su, Zixiu
# Email: szx917@gmail.com
# Date: 2021/04/26

import logging
logging.basicConfig(filename='log.txt',level=logging.DEBUG)
log = logging.getLogger("ParserGen")
from collections import defaultdict
from tabulate import tabulate

from grammar import *


# Newtype {sp.}: For all item, 0 <= pos <= len(body)
LR0ItemTuple = namedtuple("Item", ["head", "body", "pos"])

class LR0Item(LR0ItemTuple):
  def __str__(self):
    s = ["{: ^4}".format(self.head),"->"] + self.body
    s.insert( 2+self.pos, "." ) 
    return " ".join(s)

class LR0:
  def __init__(self, grammar: Grammar):
    self.grammar = grammar
    self.states = []
    self.st2id = {}  # tracking unique sets using string reps as keys
    self.actions = {} # combined lookup table for shift/reduce decisions

    # Augment grammar with a new start symbol
    start = LR0Item(START, [grammar.startSymbol, EOF], 0)

    # Build states and action table:
    closure = self.closureOf(grammar, [start])
    self.states.append(closure)
    self.st2id[self.showItemList(closure)] = 0

    newstates = [0]
    stnum = 1

    while newstates:
      st = newstates.pop(0)
      handle = () # tuple (head, body)
      gotos = {}
      for item in self.states[st]:
        l,r,p = item
        if r == []:
          log.warning("LR0 STATE{} ERROR: epsilon transition {}".format(stnum, item))
        else:
          if p >= len(r): # reduce handles
            if gotos:
              log.warning("LR0 STATE{} ERROR: shift/reduce conflict {}".format(stnum, item))
            elif handle:
              log.warning("LR0 STATE{} ERROR: reduce/reduce conflict {}".format(stnum, item))
            else:
              handle = (l, r)
          else: # shift
            if handle:
              log.warning("LR0 STATE{} ERROR: shift/reduce conflict {}".format(stnum, item))
            else:
              nxt = r[p]
              newitem = LR0Item(l,r,p+1)
              if nxt in gotos:
                gotos[nxt].append(newitem)
              else:
                gotos[nxt] = [newitem]

      if handle:
        self.actions[st] = ("reduce", handle)
      else:
        transition = {} # {sym : st id}
        for nxt, l in gotos.items():
          closure = self.closureOf(grammar, l)
          strrep = self.showItemList(closure)
          if strrep in self.st2id:
            transition[nxt] = self.st2id[strrep]
          else:
            self.states.append(closure)
            self.st2id[strrep] = stnum
            transition[nxt] = stnum
            newstates.append(stnum)
            stnum += 1
        self.actions[st] = ("shift", transition)
    # end while new states
    self.dump()
  # end __init__()

  def closureOf(self, g: Grammar, items: List[LR0Item]):
    closure = deepcopy(items)
    update = True
    begin = 0 # savepoint for scanning new entries
    visited = set()
    while update:
      update = False
      for i in range(begin,len(closure)):
        item = closure[i]
        begin += 1
        sz = len(item.body)
        # Pos out of bound
        if not 0 <= item.pos <= sz:
          log.warning("Wrong pos={}, len={}", pos, sz)
        # Legal pos
        else:
          nxt = None if item.pos == sz else item.body[item.pos]
          if nxt and nxt in g.nonTerminals and nxt not in visited:
            visited.add(nxt)
            for rhs in g.productions[nxt]:
              update = True
              if rhs == [EPSILON]:
                log.warning("Epsilon trasitions in closure:",item)
              else:
                temp = LR0Item(nxt, rhs, 0)
                closure.append(temp)
    # end while update
    return closure

  # return 0 if accept
  def parse(self, tokens: List[str]):
    tokens.append(EOF)
    ststack = [0]
    symstack = []
    st = 0
    step = 0
    it = iter(tokens)
    result = 1
    while True:
      step += 1
      log.info("--STEP {}".format(step))
      act = self.actions[st]
      if act[0] == "reduce":
        head, body = act[1]
        if symstack[-len(body):] != body:
          # should NOT ever happen?
          log.warning("REDUCE ERROR @ ST {}: stack = st{} sym{}".format(st,ststack,symstack))
          break
        else:
          if head == START:
            log.info("* ACCEPT *")
            result = 0
            break
          else:
            for i in range(len(body)):
              ststack.pop()
              symstack.pop()
            if not ststack: # should NOT ever happen
              log.warning("UNEXPECTED EMPTY STACK")
              break
            symstack.append(head)
            top = ststack[-1]
            st = self.actions[top][1][head]
            ststack.append(st)
      elif act[0] == "shift":
        ahead = next(it, None)
        if not ahead: # should NOT happend due to $ sym
          log.warning("UNEXPECTED EOF: stack = {}".format(stack))
          break
        elif ahead not in self.actions[st][1]:
          log.info("SHIFT ERROR ({}) @ ST{}: stack = st{} sym{}"\
                      .format(ahead,st,ststack,symstack))
          log.info("& REJECT &")
          break
        else:
          symstack.append(ahead)
          st = self.actions[st][1][ahead] # should always be there
          ststack.append(st)
      log.info("state = {}, stack = sts {} sym {}".format(st,ststack,symstack))
    # end while True
    return result

  def dump(self):
    print()
    self.dumpStates()
    self.dumpTable()

  def dumpStates(self):
    for i,st in enumerate(self.states):
      print("ST", i)
      print(self.showItemList(st))

  def dumpTable(self):
    empty = ""
    symbols = list(self.grammar.terminals) + [EOF] \
              + list(self.grammar.nonTerminals)
    sym2id = { sym : i for i, sym in 
                enumerate(symbols) }
    head = [""] + symbols + ["reduce"]
    stnum = len(self.states)
    out = [ [empty for i in range(len(head))] for j in range(stnum) ]
    for i in range(stnum):
      out[i][0] = str(i)
      t, x = self.actions[i]
      if t == "reduce":
        l, r = x
        out[i][-1] = " ".join( [l,"->"," ".join(r)] )
      else:
        for key, val in x.items():
          col = sym2id[key] + 1
          out[i][col] = str(val)
    print(tabulate(out, headers=head))

  def showItemList(self, l: List[LR0Item]):
    return "\n".join(str(i) for i in l)



# Augmented LR0 item w/e a lookahead set
# {sp.}: For all item, 0 <= pos <= len(body)
LR1ItemTuple = namedtuple("LR1Item", ["head", "body", "pos", "laset"])

class LR1Item(LR1ItemTuple):
  def __str__(self): # example : E -> . T E'  {'$'}
    s = ["{: ^4}".format(self.head),"->"] + self.body
    s.insert( 2+self.pos, "." ) 
    return " ".join(s) + '\t' + str(sorted(list(self.laset)))

class LR1:
  def __init__(self, grammar: Grammar):
    self.states = []
    self.st2id = {}  # tracking unique sets using string reps as keys
    self.table = {} # combined lookup table for shift/reduce decisions

    # Augment grammar with START and EOF
    g = deepcopy(grammar)
    g.terminals |= {EOF}
    self.grammar = g

    # Initialize State Zero
    temp = [ LR1Item(START, [g.startSymbol], 0, {EOF}) ]
    g.startSymbol = START

    st0 = self.closureOf(temp)
    self.states.append(st0)
    self.st2id[self.showItemList(st0)] = 0
    newstates = [0]
    stnum = 1

    while newstates:
      st = newstates.pop(0)
      gotos = defaultdict(list)
      self.table[st] = defaultdict(list)
      for item in self.states[st]:
        head,body,pos,laset = item
        if pos >= len(body): # reduce item
          for a in laset:
            self.table[st][a].append(("reduce", (head, body)))
        else: # shift item
          nxt = body[pos]
          temp = LR1Item(head, body, (pos+1), laset)
          gotos[nxt].append(temp)
      
      for nxt, go in gotos.items():
        if go != []:
          temp = self.closureOf(go)
          strrep = self.showItemList(temp)
          if strrep not in self.st2id:
            self.states.append(temp)
            self.st2id[strrep] = stnum
            newstates.append(stnum)
            self.table[st][nxt].append(("shift", stnum))
            stnum += 1
          else:
            self.table[st][nxt].append(("shift", self.st2id[strrep]))
    # end while newstates

    # report ambiguity in table
    symbols = self.grammar.terminals | self.grammar.nonTerminals
    for i in range(stnum):
      for sym in symbols:
        if len(self.table[st][sym]) > 1:
          log.warning("CONFLICT IN ST{} LA{}: {}".format(st,sym,self.table[st][sym]))
    self.dump()

  def closureOf(self, items: List[LR1Item]):
    closure = deepcopy(items)
    g = self.grammar

    update = True
    begin = 0 # savepoint for scanning new entries
    visited = set()
    while update:
      update = False
      for i in range(begin,len(closure)):
        item = closure[i]
        begin += 1
        sz = len(item.body)
        nxt = None if item.pos >= sz else item.body[item.pos]

        if nxt and nxt in g.nonTerminals \
           and nxt not in visited:
          visited.add(nxt)
          update = True
          # compute look ahead for new items
          newla = g.firstOfAll(item.body[item.pos+1:])
          if EPSILON in newla:
            newla.remove(EPSILON)

          if g.allNullable(item.body[item.pos+1:]):
            newla |= item.laset
          for rhs in g.productions[nxt]:
            if rhs == [EPSILON]:
              # collapse epsilon symbol
              rhs = []
            temp = LR1Item(nxt, rhs, 0, newla)
            closure.append(temp)
    # end while update
    return closure

  # return 0 if accept
  def parse(self, tokens: List[str]):
    log.info("LR1 parsing {}".format(tokens))
    tokens.append(EOF)
    st = 0
    ststack = [0]
    symstack = []
    step = 0
    it = iter(tokens)
    result = 1
    ahead = next(it, None)
    while True:
      step += 1
      log.info("--STEP {}".format(step))
      choices = self.table[st][ahead]
      if choices == []:
        log.info("No choices ({}) @ ST{}".format(ahead, st))
        log.info("& REJECT &")
        break
      elif len(choices) >= 2:
        log.info("Ambiguity ({}) @ ST{}: table entry {}".format(t, st, choices))
        if len(choices) == 2 and choices[0][0] != choices[1][0]:
          choice = choices[0] if choices[0][0] == "shift" else choices[1]
          log.info("|- Resolved as shift")
        else:
          log.info("|- Cannot resolve")
          break
      else:
        choice = choices[0]
      t, x = choice
      if t == "reduce":
        head, body = x
        if head == START:
          result = 0
          log.info("* ACCEPT *")
          break
        else:
          log.info("reducing {}".format(x))
          for i in range(len(body)):
            ststack.pop()
            symstack.pop()
          if not ststack: # should NOT ever happen
            log.warning("UNEXPECTED EMPTY STACK")
            break
          symstack.append(head)
          top = ststack[-1]
          if len(self.table[top][head]) != 1:
            log.warning("UNEXPECTED AMBIGUITY ON NT ({}) @ ST{}".format(head, st))
            break
          st = self.table[top][head][0][1]
          ststack.append(st)
      elif t == "shift":
        if not ahead or ahead not in self.table[st]:
          log.warning("UNEXPECT TOKEN {}".format(ahead))
          break
        else:
          log.info("shifting {}".format(x))
          symstack.append(ahead)
          st = x
          ststack.append(st)
          ahead = next(it, None)
      log.info("state = {}, stack: sts {} sym {}".format(st, ststack, symstack))
    # end while True
    return result

  def showItemList(self, l: List[LR1Item]):
    return "\n".join(str(i) for i in l)

  def dump(self):
    print()
    self.dumpStates()
    self.dumpTable()

  def dumpStates(self):
    for i, st in enumerate(self.states):
      print("ST", i)
      print(self.showItemList(st))

  def dumpTable(self):
    colwidth = 9
    symbols = list(self.grammar.terminals) \
              + list(self.grammar.nonTerminals)
    sym2id = { sym : i for i, sym in 
                enumerate(symbols) }
    head = [""] + ["{: ^{}}".format(sym,colwidth) for sym in symbols]
    stnum = len(self.states)
    out = [ [ [] for i in range(len(head))] for j in range(stnum) ]
    for i in range(stnum):
      out[i][0] = str(i)
      for sym in symbols:
        # print(self.table[i][sym])
        col = sym2id[sym] + 1
        for t, x in self.table[i][sym]:
          if t == "reduce":
            l, r = x
            out[i][col].append( " ".join( [ l, "->", " ".join(r) ] ) )
          else:
            out[i][col].append("s " + str(x))
    # printing
    print(tabulate(out, headers=head))

  def showItemList(self, l: List[LR0Item]):
    return "\n".join(str(i) for i in l)

if __name__ == "__main__":
  print("Parser...")

  terms1 = {"(", ")", "ID", "*", "DIV_OP",
            "+", EPSILON}
  nonterms1 = {"E", "E'", "T", "T'", "F"}
  productions1 = {"E":  [["T","E'"]],
                  "E'": [["+", "T", "E'"], [EPSILON]],
                  "T":  [["F", "T'"]],
                  "T'": [["*", "F", "T'"], [EPSILON]],
                  "F":  [["(", "E", ")"], ["ID"]]}
  start1 = "E"
  g1 = Grammar(terms1, nonterms1, productions1, start1)
  g1.analyze()
  print("g1 first:",g1.first)
  print("g1 follow:",g1.follow)

  terms2 = {"(", ")", "+", "ID"}
  nonterms2 = {"E", "T",}
  productions2 = {"E":  [["E", "+", "T"], ["T"]],                  
                  "T":  [["(", "E", ")"], ["ID"]]}
  start2 = "E"
  g2 = Grammar(terms2, nonterms2, productions2, start2)
  g2.analyze()
  lr0 = LR0(g2)

  terms3 = {"c", "d"}
  nonterms3 = {"S", "C"}
  productions3 = {"S" : [["C", "C"]],               
                  "C" : [["c", "C"], ["d"]]}
  start3 = "S"
  g3 = Grammar(terms3, nonterms3, productions3, start3)

  terms4 = {"=", "*", "id"}
  nonterms4 = {"S", "L", "R"}
  productions4 = {"S" : [["L", "=", "R"], ["R"]],               
                  "L" : [["*", "R"], ["id"]],
                  "R" : [["L"]]}
  start4 = "S"
  g4 = Grammar(terms4, nonterms4, productions4, start4)
  # tokens = [[] for i in range(10)]
  # tokens[0] = []
  # tokens[1] = ["ID"]
  # tokens[2] = "ID + ID".split()
  # tokens[3] = "( ID )".split()
  # tokens[4] = "( ID + ID ) + ID".split()
  # tokens[5] = "ID + ( ID + ID )".split()
  # tokens[6] = "ID + ( )".split()
  # tokens[7] = "( ( ID )".split()

  # for l in tokens:
  #   log.info("...parsing {}...".format(l[:6]))
  #   lr0.parse(l)
  #   log.info("")
  lr1input = "id = id"

  lr0 = LR0(g4)
  lr0.parse(lr1input.split())

  lr1 = LR1(g4)
  lr1.parse(lr1input.split())
