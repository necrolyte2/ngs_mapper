#!/usr/bin/env python

import re
import sys
import subprocess
import os

def parse_args( args=sys.argv[1:] ):
    # Arguments that need to be entered into the command line
    import argparse
    parser = argparse.ArgumentParser(description="Variant caller")

    parser.add_argument(
        dest='bam',
        help='Bam file path'
    )

    parser.add_argument(
        '-o',
        dest='output',
        default='varient_called_file.vcf',
        help='Output file name[Default: varient_called_file.vcf]'
    )

    parser.add_argument(
        dest='reference',
        help='Path to reference file'
    )

    parser.add_argument(
        '-b',
        dest='Alt_Ref_Ratio',
        default=0.19,
        help='Require the ratio of alt/ref above a specified threashold[Default: 0.19]'
    )

    parser.add_argument(
        '-bq',
        dest='base_quality',
        default=20,
        help='Require the base quality threashold[Default: 20]'
    )

    parser.add_argument(
        '-mq',
        dest='map_quality',
        default=25,
        help='Require the map quality threashold[Default: 25]'
    )

    parser.add_argument(
        '-s',
        dest='strand_bias',
        default=0.0001,
        help='Require the map strand bias threashold[Default: 0.0001]'
    )

    parser.add_argument(
        '-a',
        dest='reads',
        default=10,
        help='Require the least number of reads supporting each strand for alternative allele[Default: 10]'
    )

    return parser.parse_args( args )

def main( args ):
    # Input the required information
    # Alignment file
    alignment_bam = args.bam 
    # The out put file - must end in .vcf
    output_VCF_File = args.output
    # Reference file
    ref_fa = args.reference 
    # Alt:Ref file
    alt_ref = args.Alt_Ref_Ratio
    # Base Quality file
    base = args.base_quality 
    # Map Quality file
    mapq = args.map_quality
    # Strand Bias file
    strand = args.strand_bias
    # Supporting reads file
    read = args.reads
    # call runs an external program and waits for it to quit
    from subprocess import call 
    # java jar SNVerIndividual -i xxxx.bam -o output_vcf -r xxxx.fa -b 0.19 -bq 20 -mq 25 -s 0.0001 -a 10
    command = "SNVer -i {} -o {} -r {} -b {} -bq {} -mq {} -s {} -a {}".format(alignment_bam,output_VCF_File,ref_fa,alt_ref,base,mapq,strand,read)
    # shell=True is so you can handle redirects like in the 3rd command
    print command
    exit( call(command, shell=True) )

if __name__ == '__main__':
    args = parse_args()
    main( args )