import common
import fixtures

from nose.tools import eq_, raises
from nose.plugins.attrib import attr
from mock import MagicMock, patch, Mock, call

from os.path import *
import os
from ngs_mapper.compat import OrderedDict

class Base(common.BaseBamRef):
    modulepath = 'ngs_mapper.stats_at_refpos'

    def setUp( self ):
        super(Base,self).setUp()
        self.mp = {1046: join( fixtures.THIS, 'fixtures', 'mpileup_1046.txt' )}
        self.bam = self.__class__.bam

class StatsAtPos(Base):
    def _doit( self, res, eb, e ):
        # Ensure keys are same and in same order
        eq_( eb.keys(), res['Bases'].keys() )

        for base, valuesd in eb.iteritems():
            for k,v in valuesd.items():
                eq_( v, res['Bases'][base][k], "{0} != {1} for {2}".format(v, res['Bases'][base][k], k) )

        for k in e:
            eq_( e[k], res[k] )

class TestStatsAtPos(StatsAtPos):
    functionname = 'stats_at_pos'

    def test_func_works( self ):
        ref = 'Den1/U88535_1/WestPac/1997/Den1_1'
        pos = '6109'
        regionstr = '{0}:{1}-{2}'.format(ref,pos,pos)
        res = self._C( self.bam, regionstr, 0, 0, 100000 )
        #Den1/U88535_1/WestPac/1997/Den1_1  6109    N   13  GgnGgggggtGgg   CB#GHHHHG2GHH
        eb = OrderedDict([
                ('G',{'AvgBaseQ':37.73,'AvgMapQ':60.0,'Depth':11,'PctTotal':84.62}),
                ('T',{'AvgBaseQ':17.0,'AvgMapQ':60.0,'Depth':1,'PctTotal':7.69}),
                ('N',{'AvgBaseQ':2.0,'AvgMapQ':60.0,'Depth':1,'PctTotal':7.69})
            ])
        e = {
            'Bases': eb,
            'AvgMapQ': 60.0,
            'AvgBaseQ': 33.38,
            'TotalDepth': 13
        }
        self._doit( res, eb, e )

class TestCompileStats(Base):
    functionname = 'compile_stats'

    def test_func_works( self ):
        stats = {
            'depth': 1000,
            'mqualsum': 50*900+60*100,
            'bqualsum': 30*900+40*100,
            'G': {'mapq': [50]*900, 'baseq': [30]*900},
            'A': {'mapq': [60]*100, 'baseq': [40]*100}
        }
        res = self._C( stats )

        eq_( stats['depth'], res['TotalDepth'] )
        eq_( 51.0, res['AvgMapQ'] )
        eq_( 31.0, res['AvgBaseQ'] )

        g = res['Bases']['G']
        eq_( 900, g['Depth'] )
        eq_( 50.0, g['AvgMapQ'] )
        eq_( 30.0, g['AvgBaseQ'] )
        eq_( 90.0, g['PctTotal'] )

        a = res['Bases']['A']
        eq_( 100, a['Depth'] )
        eq_( 60.0, a['AvgMapQ'] )
        eq_( 40.0, a['AvgBaseQ'] )
        eq_( 10.0, a['PctTotal'] )

import mock
class TestMain(StatsAtPos):
    functionname = 'main'

    def setUp(self):
        self.patch_argparse = mock.patch('ngs_mapper.stats_at_refpos.argparse')
        self.mock_argparse = self.patch_argparse.start()
        self.args = mock.Mock()
        self.mock_argparse.ArgumentParser.return_value.parse_args = self.args

    def tearDown(self):
        self.patch_argparse.stop()

    @patch('ngs_mapper.stats_at_refpos.stats_at_pos')
    def test_unit_runs( self, stats_at_pos ):
        self.args.return_value = Mock(
            regionstr='ref1:1-1',
            bamfile='somefile.bam',
            minmq=0,
            minbq=0,
            maxd=100000
        )
        self._C()

    def test_func_runs( self ):
        self.args.return_value = Mock(
            bamfile=self.bam,
            regionstr='Den1/U88535_1/WestPac/1997/Den1_1:6109-6109',
            minmq=0,
            minbq=0,
            maxd=100000
        )
        eb = OrderedDict([
                ('G',{'AvgBaseQ':37.73,'AvgMapQ':60.0,'Depth':11,'PctTotal':84.62}),
                ('T',{'AvgBaseQ':17.0,'AvgMapQ':60.0,'Depth':1,'PctTotal':7.69}),
                ('N',{'AvgBaseQ':2.0,'AvgMapQ':60.0,'Depth':1,'PctTotal':7.69})
            ])
        e = {
            'Bases': eb,
            'AvgMapQ': 60.0,
            'AvgBaseQ': 33.38,
            'TotalDepth': 13
        }
        res = self._C()
        self._doit( res, eb, e )

    def test_func_filters_minmq( self ):
        self.args.return_value = Mock(
            bamfile=self.bam,
            regionstr='Den1/U88535_1/WestPac/1997/Den1_1:6109-6109',
            minmq=61,
            minbq=0,
            maxd=100000
        )
        res = self._C()
        #Den1/U88535_1/WestPac/1997/Den1_1  6109    N   13  GgnGgggggtGgg   CB#GHHHHG2GHH
        eb = OrderedDict([
                #('G',{'AvgBaseQ':0.0,'AvgMapQ':37.73,'Depth':11,'PctTotal':84.62}),
                #('T',{'AvgBaseQ':0.0,'AvgMapQ':17.0,'Depth':1,'PctTotal':7.69}),
                #('N',{'AvgBaseQ':0.0,'AvgMapQ':2.0,'Depth':1,'PctTotal':7.69})
            ])
        e = {
            'Bases': eb,
            'AvgMapQ': 0.0,
            'AvgBaseQ': 0.0,
            'TotalDepth': 0
        }
        self._doit( res, eb, e )

    def test_func_filters_minbq( self ):
        self.args.return_value = Mock(
            bamfile=self.bam,
            regionstr='Den1/U88535_1/WestPac/1997/Den1_1:6109-6109',
            minmq=0,
            minbq=30,
            maxd=100000
        )
        res = self._C()
        #Den1/U88535_1/WestPac/1997/Den1_1  6109    N   13  GgnGgggggtGgg   CB#GHHHHG2GHH
        eb = OrderedDict([
                ('G',{'AvgBaseQ':37.73,'AvgMapQ':60.0,'Depth':11,'PctTotal':100.0}),
                #('T',{'AvgBaseQ':0.0,'AvgMapQ':17.0,'Depth':1,'PctTotal':7.69}),
                #('N',{'AvgBaseQ':0.0,'AvgMapQ':2.0,'Depth':1,'PctTotal':7.69})
            ])
        e = {
            'Bases': eb,
            'AvgMapQ': 60.0,
            'AvgBaseQ': 37.73,
            'TotalDepth': 11
        }
        self._doit( res, eb, e )
