# -*- coding: utf-8 -*-

# Find and analyze rhymes in the corpus RNC
# Building graph database

import codecs
import os
import re
from lxml import etree
from transcribe import Transcription
from py2neo import Graph
from py2neo import authenticate

class Rhymes:
    def __init__(self):
        self.graph = Graph()
        self.root_name = ''  # Start folder
        self.parsed = codecs.open('parsed.csv', 'w', 'utf-8')

    # Transform into transcription
    def transcribe(self, word, flag):
        t = Transcription()
        t.word = word
        t.transform(flag)
        # flag = 1 -- look up the word in yo_list and replace e with yo if possible
        # flag = 0 -- do nothing with e
        return t

    # Replace e with yo
    def yo_substitution(self,  i, j, cur_rhymes, trans1, trans2, stress1, stress2, creation_date):
        if (trans1.transcription[stress1-1] == u'е' and trans2.transcription[stress2-1] == u'о'):
            trans1 = self.transcribe(cur_rhymes[i], 1)
        if (trans1.transcription[stress1-1] == u'о' and trans2.transcription[stress2-1] == u'е'):
            trans2 = self.transcribe(cur_rhymes[j], 1)
        if (trans1.transcription[stress1-1] == u'е' and trans2.transcription[stress2-1] == u'е') and \
                int(creation_date) > 1828:
            trans1 = self.transcribe(cur_rhymes[i], 1)
            trans2 = self.transcribe(cur_rhymes[j], 1)
        return trans1, trans2

    # Open or closed
    def openness(self, trans1, trans2, properties, flag):
        if len(trans1.transcription) > 1:
            num1 = -1
        else:
            num1 = 0

        if len(trans2.transcription) > 1:
            num2 = -1
        else:
            num2 = 0

        if (trans1.transcription[num1] in trans1.word_consonants or trans1.transcription[num1] == '\'') \
                and (trans2.transcription[num2] in trans2.word_consonants or trans2.transcription[num2] == '\''):
                properties.append('closed')

        elif (trans1.transcription[num1] in trans1.word_vowels and trans2.transcription[num2] in trans2.word_vowels[num2]) or \
             (trans1.transcription[num1] == trans2.transcription[num2] == u'`'):
                properties.append('open')
        else:
            properties.append('-')
            flag = 0
        return properties, flag

    # Exact or inexact
    def exactness(self, trans1, trans2, stress1, stress2, properties, flag):
        exactness = 0
        min_len = min(len(trans1.transcription[stress1+1:]), len(trans2.transcription[stress2+1:]))
        max_len = max(len(trans1.transcription[stress1+1:]), len(trans2.transcription[stress2+1:]))
        if max_len - min_len == 0:
            k = 1
            while k <= min_len:
                if trans1.transcription[stress1+k] == trans2.transcription[stress2+k]:
                    exactness += 1
                k += 1
            if k-exactness == 1:
                res_exact = 'exact'
            else:
                res_exact = 'inexact'
            properties.append(res_exact)
            properties.append(str(k-exactness))
            if k-exactness <= 2:
                flag = 1
            if res_exact == 'inexact':
                properties.append('poor')
                self.assonance(trans1, trans2, properties)
            if res_exact == 'exact':
                self.richness(trans1, trans2, stress1, stress2, properties)
        return properties, flag

    # Assonance
    def assonance(self, trans1, trans2, properties):
        assonance_flag = 1
        for v1 in trans1.word_vowels:
            for v2 in trans2.word_vowels:
                if v1 != v2:
                    assonance_flag = 0
                    break
        if assonance_flag == 1:
            properties.append('-')
            properties.append('assonance')
            properties.append('-')
        else:
            properties.append('-')
            properties.append('-')
            properties.append('-')
        return properties

    # Dissonance
    def dissonance(self, trans1, trans2, properties, flag):
        dis_flag = 1
        for cons1 in trans1.word_consonants:
            for cons2 in trans2.word_consonants:
                if cons1 != cons2:
                    dis_flag = 0
                    break
        if dis_flag == 1:
            properties.append('-')
            properties.append('-')
            properties.append('-')
            properties.append('-')
            properties.append('-')
            properties.append('dissonance')
            flag = 1
        return properties, flag

    # Rich or poor
    def richness(self, trans1, trans2, stress1, stress2, properties):
        if trans1.transcription[stress1-2] == trans2.transcription[stress2-2]:
            if trans1.transcription[stress1-2] != '\'':
                properties.append('rich')
                self.depth(trans1, trans2, properties)
            else:
                if trans1.transcription[stress1-3] == trans2.transcription[stress2-3]:
                    properties.append('rich')
                    properties.append('-')
                    properties.append('-')
                    properties.append('-')
                else:
                    properties.append('poor')
                    properties.append('-')
                    properties.append('-')
                    properties.append('-')
        else:
            properties.append('poor')
            properties.append('-')
            properties.append('-')
            properties.append('-')
        return properties

    # Deep or not
    def depth(self, trans1, trans2, properties):
        if len(trans1.pre_vowels) > 0 and len(trans2.pre_vowels) > 0:
            if trans1.pre_vowels[-1] == trans2.pre_vowels[-1]:
                properties.append('deep')
                properties.append('-')
                properties.append('-')
            else:
                properties.append('-')
                properties.append('-')
                properties.append('-')
        else:
            properties.append('-')
            properties.append('-')
            properties.append('-')
        return properties

    # Rhyming type
    def rhyming(self, i, j, properties):
        if j-i == 1:
            properties.append('paired')
        elif j-i == 2:
            properties.append('crossed')
        elif j-i == 3:
            properties.append('encircling')
        else:
            properties.append('-')
        return properties

    # Position type
    def position(self, trans1, trans2, stress1, stress2, properties):
        vowels1_after = 0
        for sound in trans1.transcription[stress1+1:len(trans1.transcription)]:
            if sound in trans1.all_vowels or sound in u'ьъ':
                vowels1_after += 1
        vowels2_after = 0
        for sound in trans2.transcription[stress2+1:len(trans2.transcription)]:
            if sound in trans2.all_vowels or sound in u'ьъ':
                vowels2_after += 1
        if vowels1_after == 0 and vowels2_after == 0:
            properties.append('male')
        elif vowels1_after == 1 and vowels2_after == 1:
            properties.append('female')
        elif vowels1_after == 2 and vowels2_after == 2:
            properties.append('dactyl')
        elif vowels1_after >= 3 and vowels2_after >= 3:
            properties.append('hyperdactyl')
        else:
            properties.append('-')
        return properties

    # Full rhyme analysis
    def rhyme_analysis(self, i, j, cur_rhymes, trans1, trans2, stress1, stress2, creation_date, properties, flag):
        self.yo_substitution(i, j, cur_rhymes, trans1, trans2, stress1, stress2, creation_date)
        flag = self.openness(trans1, trans2, properties, flag)[1]

        if trans1.transcription[stress1-1] == trans2.transcription[stress2-1]:

            # If stressed vowel is the last sound in the line
            if stress1 == len(trans1.transcription) and stress2 == len(trans2.transcription):
                flag = 1
            else:
                flag = self.exactness(trans1, trans2, stress1, stress2, properties, flag)[1]
        else:
            flag = self.dissonance(trans1, trans2, properties, flag)[1]
        self.rhyming(i, j, properties)
        self.position(trans1, trans2, stress1, stress2, properties)
        return properties, flag

    # Print record while extracting and classifying
    def print_record(self, name, i, j, cur_rhymes, properties):
        new_record = name + ','
        new_record += cur_rhymes[i].lower() + ',' + cur_rhymes[j].lower() + ','
        new_record += ','.join(properties)
        print new_record.replace(',', '\t')
        self.parsed.write(new_record + '\n')

    # Create nodes and relationship
    def create_nodes(self, name, i, j, cur_rhymes, properties):
        self.graph.cypher.execute("""
        MERGE (word1:Word { word: '""" + cur_rhymes[i].lower() + """' })
        MERGE (word2:Word { word: '""" + cur_rhymes[j].lower() + """' })
        CREATE UNIQUE (word1)-[r:RHYME {path: '""" + name + """',
                                        openness: '""" + properties[0] + """',
                                        exactness: '""" + properties[1] + """',
                                        degree_exactness: '""" + properties[2] + """',
                                        richness: '""" + properties[3] + """',
                                        depth: '""" + properties[4] + """',
                                        assonance: '""" + properties[5] + """',
                                        dissonance: '""" + properties[6] + """',
                                        rhyming: '""" + properties[7] + """',
                                        position: '""" + properties[8] + """',
                                        meter1: '""" + properties[9] + """',
                                        meter2: '""" + properties[10] + """'
                                         }]->(word2)
        """)

        self.graph.cypher.execute("CREATE INDEX ON :Word(word)")

    # Find rhymes
    def find_rhymes(self, i, j, cur_rhymes, cur_meter, name, creation_date):
        flag = 0
        properties = []
        trans1 = self.transcribe(cur_rhymes[i], 0)
        trans2 = self.transcribe(cur_rhymes[j], 0)
        stress1 = trans1.transcription.index('`')
        stress2 = trans2.transcription.index('`')

        if trans1 is not None and trans2 is not None:
            try:
                flag = self.rhyme_analysis(i, j, cur_rhymes, trans1, trans2, stress1, stress2, creation_date, properties, flag)[1]
            except:
                pass

            if flag == 1:
                try:
                    properties.append(cur_meter[i])
                    properties.append(cur_meter[j])
                except IndexError:
                    properties.append("")
                    properties.append("")
            #   Uncomment if needed to create new record into Neo4j DB
            #    self.create_nodes(name, i, j, cur_rhymes, cur_meter, properties)
                self.print_record(name, i, j, cur_rhymes, properties)


    # Analyse all documents
    def analyse(self):
        done = 1
        self.parsed.write('path,word1,word2,openness,exactness,degree_exactness,richness,depth,assonance,dissonance,rhyming,position,meter1,meter2\n')
        all = sum([len(files) for r, d, files in os.walk(self.root_name)])
        print all, 'files to analyse'

        # Uncomment if needed to start parsing excluding already parsed files
        # exclude = frozenset([])
        for root, dirs, files in os.walk(self.root_name):
            # dirs[:] = [d for d in dirs if d not in exclude]
            # files[:] = [f for f in files if f not in exclude]
            for name in files:
                print os.path.abspath(os.path.join(root, name))
                path = os.path.abspath(os.path.join(root, name))
                if 'xix' or 'xx' in path:
                    creation_date = '1900'
                else:
                    creation_date = ''

                f = codecs.open(path, 'r', 'cp1251')
                text = f.read().encode('utf-8')
                f.close()

                # Parse the document
                tree_root = etree.XML(text, etree.HTMLParser())
                cur_rhymes = []
                cur_meter = []
                for d in tree_root.iter():

                    # Find date
                    if creation_date == '':
                        if d.tag == 'meta' and 'name' in d.attrib and (d.attrib['name'] == 'created' or d.attrib['name'] == 'date'):
                            raw_date = d.attrib['content']
                            date = re.compile('[0-9]{4}')
                            if len(raw_date) > 4:
                                search_date = re.search(date, raw_date)
                                if search_date is not None:
                                    creation_date = search_date.group(0)
                            else:
                                creation_date = raw_date

                    # Collect all words in rhyme-zones
                    if d.tag == 'p' and 'class' in d.attrib and d.attrib['class'] == 'verse':
                        for child in d.iterchildren():
                            if child.tag == 'line':
                                cur_meter.append(child.attrib['meter'])

                            if child.tag == 'rhyme-zone':
                                if child.tail is not None:

                                    # Word in a rhyme position
                                    if child.tail is not None:
                                        word = child.tail.strip(u'.…,“«»?()[]{}<>!:;,-_ "”0123456789 ')
                                        if u'̀' in word and re.match(u"[-А-Яа-я̀]", word):
                                            cur_rhymes.append(word)

                for i in range(len(cur_rhymes)):
                    j = 1
                    while j <= 5 and i+j < len(cur_rhymes):
                        self.find_rhymes(i, i+j, cur_rhymes, cur_meter, name, creation_date)
                        j += 1

                print str(round((done/float(all))*100, 4)) + '% of all files done (' + str(done) + ' out of ' + str(all) + ')'
                done += 1

# Uncomment if needed to create new records into Neo4j
#authenticate("localhost:7474", "neo4j", "neo4j")
rhymes = Rhymes()
rhymes.root_name = '.\\xx'
rhymes.analyse()
