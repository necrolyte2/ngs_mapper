#!/usr/bin/env python

import subprocess
import os
import argparse
import sys
from os.path import basename, join, isdir, dirname
from glob import glob
import tempfile
import reads

import log
lconfig = log.get_config()
logger = log.setup_logger( 'trim_reads', lconfig )

def main( args ):
    trim_reads_in_dir(
        args.readsdir,
        args.q,
        args.outputdir
    )

def trim_reads_in_dir( *args, **kwargs ):
    '''
        Trims all read files in a given directory and places the resulting files into out_path directory

        @param readdir - Directory with read files in it(sff and fastq only)
        @qual_th - What to pass to cutadapt -q
        @out_path - Output directory path
    '''
    readdir = args[0]
    qual_th = args[1]
    out_path = args[2]

    # Only sff and fastq files
    reads = [f for f in os.listdir(readdir) if f.endswith('sff') or f.endswith('fastq')]
    # Make out_path
    if not isdir( out_path ):
        os.mkdir( out_path )
    # Trim all the reads
    for read in reads:
        reado = read.replace('.sff','.fastq')
        try:
            trim_read( join(readdir,read), qual_th, join(out_path,reado) )
        except subprocess.CalledProcessError as e:
            print e.output
            raise e

def trim_read( *args, **kwargs ):
    '''
        Trims the given readpath file and places it in out_path
        If out_path not given then just put it in current directory with the same basename

        @param readpath - Path to the read to trim .fastq and .sff support only
        @param qual_th - Quality threshold to trim reads on
        @param out_path - Where to put the trimmed file

        @returns path to the trimmed fastq file
    '''
    readpath = args[0]
    qual_th = args[1]
    if len(args) == 3:
        out_path = args[2]
    else:
        out_path = None

    from Bio import SeqIO
    tfile = None
    if out_path is None:
        out_path = basename( readpath ).replace('.sff','.fastq')
    logger.debug( "Using {} as the output path".format(out_path) )
    
    # Keep the original name for later
    orig_readpath = readpath

    # Convert sff to fastq
    if readpath.endswith('.sff'):
        logger.debug( "Converting {} to fastq".format(readpath) )
        # Just put in temp location then remove later
        _, tfile = tempfile.mkstemp(prefix='trimreads',suffix='sff.fastq')
        try:
            # Clip adapter based on clip_qual values in sff
            nwritten = reads.sffs_to_fastq( [readpath], tfile, True )
        except AssertionError as e:
            # Ignore the stupid sff bug in BioPython
            pass
        readpath = tfile

    # Run cutadapt on the file
    stats_file = join( dirname(dirname(out_path)), 'trim_stats', basename(orig_readpath) + '.trim_stats' )
    if not isdir(dirname(stats_file)):
        os.makedirs( dirname(stats_file) )
    run_cutadapt( readpath, stats=stats_file, o=out_path, q=qual_th )

    # Clean up temp file
    if tfile:
        os.unlink(tfile)

    return out_path

def run_cutadapt( *args, **kwargs ):
    '''
        Runs cutadapt with the given arguments and kwargs
        
        @param - fastq file to trim
        @param - output file location
        @param q - Quality threshold

        @returns the stderr output from cutadapt
    '''
    outpath = kwargs.get('o')
    cmd = ['cutadapt', '-o', outpath, '-q', str(kwargs.get('q')), args[0]]
    out_stats = kwargs.get( 'stats', outpath + '.trim_stats' )
    fout = open(out_stats,'wb')
    # Write stdout to output argument(should be fastq)
    # Allow us to read stderr which should be stats from cutadapt
    logger.debug( "Running {}".format(cmd) )
    logger.debug( "Sending stdout to {}".format(out_stats) )
    p = subprocess.Popen( cmd, stdout=fout, stderr=subprocess.PIPE )
    # Only stderr should be available
    _,se = p.communicate()
    if p.returncode != 0:
        e = subprocess.CalledProcessError(p.returncode,' '.join(cmd), se)
        raise e
    return se

def parse_args( args=sys.argv[1:] ):
    parser = argparse.ArgumentParser(
        description='Trims reads'
    )

    parser.add_argument(
        dest='readsdir',
        help='Read or directory of read files'
    )

    qual_default=20
    parser.add_argument(
        '-q',
        dest='q',
        default=qual_default,
        help='Quality threshold to trim[Default:{}]'.format(qual_default)
    )

    outputdir_default='trimmed_reads'
    parser.add_argument(
        '-o',
        dest='outputdir',
        default=outputdir_default,
        help='Where to output the resulting files[Default:{}]'.format(outputdir_default)
    )

    return parser.parse_args( args )

if __name__ == '__main__':
    main(parse_args())
