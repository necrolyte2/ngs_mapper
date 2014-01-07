#!/usr/bin/env python

## Untested

from subprocess import Popen, PIPE
import argparse
import sys
import itertools
from collections import OrderedDict

def main(args):
    stats_at_pos( args.refpos, args.bamfile, args.minqual, args.maxd )

def parse_args(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(
        description='''Gives stats about a given site in a bam file''',
        epilog=u'''
            Some things to note at this time:
             Still confused about how the samtools manpage for mpileup says that the output should
             be:
                In the pileup format (without -uor-g), each line represents a genomic position, consisting of chromosome name, coordinate, reference base, read bases, read qualities and alignment mapping qualities. Information on match, mismatch, indel, strand,  mapping  quality  and
                 start  and  end of a read are all encoded at the read base column. At this column, a dot stands for a match to the reference base on the forward strand, a comma for a match on the reverse strand, a '>' or '<' for a reference skip, 'ACGTN' for a mismatch on the forward
                 strand and 'acgtn' for a mismatch on the reverse strand. A pattern '\+[0-9]+[ACGTNacgtn]+' indicates there is an insertion between this reference position and the next reference position. The length of the insertion is given by the integer in the pattern, followed  by
                 the inserted sequence. Similarly, a pattern '-[0-9]+[ACGTNacgtn]+' represents a deletion from the reference. The deleted bases will be presented as '*' in the following lines. Also at the read base column, a symbol '^' marks the start of a read. The ASCII of the char-
                 acter following '^' minus 33 gives the mapping quality. A symbol '$' marks the end of a read segment.
            However, instead it seems you get chromosome name, coordinate, reference base, read depth, read bases, mapping quality
            Not sure how to get read base qualities as well like it says, but that would be great
            
            Insertions and deletions in the read bases (+/-[0-9][a-zA-Z]+) will simply have mapping quality 0 inserted for them by this script. Good idea or not...
        '''
    )

    parser.add_argument(
        dest='bamfile',
        help='Bam file path for stats'
    )

    parser.add_argument(
        dest='refpos',
        type=int,
        help='Position on reference to get stats for'
    )

    parser.add_argument(
        '-Q',
        '--min-qual',
        dest='minqual',
        default=25,
        help='Minimum read quality to be included in stats[Default: 25]'
    )

    parser.add_argument(
        '-m',
        '--max-depth',
        dest='maxd',
        default=100000,
        help='Maximum read depth at position to use[Default: 100000]'
    )
    
    return parser.parse_args(args)

def mpileup_pysam( bamfile, regionstr, minqual=25, maxd=10000 ):
    import pysam
    samfile = pysam.Samfile( bamfile )
    return samfile.pileup( region=regionstr )

def mpileup_popen( bamfile, regionstr=None, minqual=25, maxd=100000 ):
    cmd = ['samtools','mpileup','-Q','{}'.format(minqual),'-d','{}'.format(maxd)]
    if regionstr:
        cmd += ['-r',regionstr]
    cmd.append( bamfile )
    p = Popen( cmd, stdout=PIPE )
    return p.stdout

def mpileup( bamfile, regionstr=None, minqual=25, maxd=100000 ):
    return mpileup_popen( bamfile, regionstr, minqual, maxd )

def indel( sequence, pos, quallist, qualpadding=0 ):
    ''' 
        Returns new quallist with inserted quals
    
        >>> from nose.tools import eq_
        >>> quals = [1,1,1,1]
        >>> seq = 'abc+2aag'
        >>> r = indel( seq, 3, quals )
        >>> e = [1,1,1,0,0,1]
        >>> eq_( e, r, "Insert in middle {} != {}".format(e,r) )
        >>> seq = '+2aaAAAA'
        >>> r = indel( seq, 0, quals )
        >>> e = [0,0,1,1,1,1]
        >>> eq_( e, r, "Insert at beginning {} != {}".format(e,r) )
        >>> seq = 'AAAA+2aa'
        >>> e = [1,1,1,1,0,0]
        >>> r = indel( seq, 4, quals )
        >>> eq_( e, r,"Insert at end {} != {}".format(e,r) )
    '''
    # Should be how many as pos is the index of the +/- in sequence
    n = int(sequence[pos+1])
    if sequence[pos] == '-':
        raise ValueError( "I don't know how to do deletions yet" )
    elif sequence[pos] == '+':
        left = quallist[:pos]
        right = quallist[pos:]
        insert = [qualpadding]*n
        quallist = left + insert + right

    return quallist

def stats_at_pos( refpos, bamfile, minqual, maxd ):
    stats = stats_at_pos_popen( refpos, bamfile, minqual, maxd )
    print "Maximum Depth: {}".format(maxd)
    print "Minumum Quality Threshold: {}".format(minqual)
    base_stats = compile_stats( stats )
    print "Average Mapping? Quality: {}".format(base_stats['AvgMapQ'])
    print "Depth: {}".format(base_stats['TotalDepth'])
    for base, bstats in base_stats['Bases'].iteritems():
        print "Base: {}".format(base)
        print "\tDepth: {}".format( bstats['Depth'] )
        print "\tAverage Mapping Quality: {}".format( bstats['AvgMapQ'] )
        print "\tAverage Read Quality: {}".format( bstats['AvgReadQ'] )
        print "\t% of Total: {}".format( bstats['PctTotal'] )

    return base_stats

def stats_at_pos_popen( refpos, bamfile, minqual, maxd ):
    base_stats = {}
    pile = mpileup( bamfile, minqual=minqual, maxd=maxd )
    for line in pile:
        line = line.rstrip().split()
        pos = int(line[1])
        depth = int(line[3])
        if pos != refpos:
            continue
        bases = []
        quals = [ord(q)-33 for q in line[5]]
        for i in range(len(line[4])):
            b = line[4][i]
            if b.upper() not in 'ATGC*N':
                #print "Skipping unknown base '{}'".format(b)
                # Do insert/delete
                if b in '+-':
                    quals = indel( line[4], i, quals )
                continue
            bases.append(b)
        bq = [x for x in itertools.izip_longest(bases,quals, fillvalue='!')]
        assert len(quals) == len(bases), "Number of quals {} !=  number of bases {}\n{}".format(len(quals),len(bases),line)

        # Stats
        stats = {
            'depth': 0,
            'mqualsum': 0.0,
            'rqualsum': 0.0
        }
        for base, qual in bq:
            base = base.upper()
            if base not in stats:
                stats[base] = []
            stats[base].append( qual )
            stats['depth'] += 1
            stats['mqualsum'] += float(qual)

        return stats

def compile_stats( stats ):
    '''
        @param stats - {'depth': 0, 'mqualsum': 0, 'rqualsum': 0, 'ATGCN*..': [quals]} depth is total depth at a position and qualsum is sum of all quality scores rqualsum is read quality sums ATGCN* will be keys for each base seen and the list of quality scores for them
        @return - Dictionary of stats at each base and overall stats {'Bases': {'A': [quals], 'depth': 0, 'avgqual': 0.0}}
    '''
    base_stats = {}
    base_stats['TotalDepth'] = stats['depth']
    base_stats['AvgMapQ'] = round(stats['mqualsum']/stats['depth'],2)
    base_stats['AvgReadQ'] = round(stats['rqualsum']/stats['depth'],2)
    base_stats['Bases'] = {}
    for base, quals in stats.iteritems():
        if base not in ('depth','mqualsum','rqualsum'):
            if base not in base_stats['Bases']:
                base_stats['Bases'][base] = {}
            base_stats['Bases'][base]['Depth'] = len(quals)
            base_stats['Bases'][base]['AvgMapQ'] = round(float(sum(quals))/len(quals),2)
            base_stats['Bases'][base]['AvgReadQ'] = round(0.0,2)
            base_stats['Bases'][base]['PctTotal'] = round((float(len(quals))/stats['depth'])*100,2)

    # Quit out of loop we are done
    # Order bases by PctTotal descending
    sorted_bases = sorted( base_stats['Bases'].items(), key=lambda x: x[1]['PctTotal'], reverse=True )
    base_stats['Bases'] = OrderedDict(sorted_bases)
    return base_stats

if __name__ == '__main__':
    main(parse_args())
