# Install setuptools automagically from the interwebz
from ez_setup import use_setuptools
use_setuptools()

from glob import glob
import sys
from os.path import join

from setuptools import setup, find_packages
import setuptools
from setuptools.command.bdist_egg import bdist_egg as _bdist_egg
from setuptools.command.develop import develop as _develop

from version import __version__

class InstallSystemPackagesCommand(setuptools.Command):
    '''
    Custom setup.py install keyword to initiate system-package installation
    '''
    user_options = []
    description = 'Installs all system packages via the package manager(Requires super-user)'

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from miseqpipeline.dependency import (
            install_system_packages,
            get_distribution_package_list,
            UserNotRootError
        )
        try:
            system_packages = get_distribution_package_list('system_packages.lst')
            install_system_packages(system_packages)
        except UserNotRootError as e:
            print "You need to be root to install system packages"

class PipelineInstallCommand(_bdist_egg):
    '''
    Custom install command which should install everything needed
    '''
    description = 'Installs the pipeline'

    def run(self):
        # Numpy doesn't seem to install correctly through the install_requires section
        # https://github.com/numpy/numpy/issues/2434
        print "Installing numpy"
        self.pip_install( 'numpy==1.8.0' )
        # Run normal setuptools install
        print "Installing pipeline"
        _bdist_egg.run(self)
        # Install dependencies outside of python
        # May require that setup_requires has been processed
        # so has to come after _bdist_egg.run
        print "Installing ext deps"
        self._install_external_dependencies()

    def _install_external_dependencies(self):
        # URLs for dependencies
        bwa_url = 'https://github.com/lh3/bwa'
        samtools_url = 'https://github.com/samtools/samtools'
        trimmomatic_url = 'http://www.usadellab.org/cms/uploads/supplementary/Trimmomatic/Trimmomatic-0.32.zip'

        # Install samtools and bwa
        from miseqpipeline.dependency import (
                install_samtools,
                install_bwa,
                install_trimmomatic
        )

        # Prefix path for installation
        prefix = sys.prefix
        bindir = join(prefix,'bin')
        libdir = join(prefix,'lib')

        # Install all dependencies outside fo pypi
        install_bwa(bwa_url, '0.7.6a', prefix)
        install_samtools(samtools_url, '96b5f2294ac005423', prefix)
        install_trimmomatic(trimmomatic_url, libdir)

    def pip_install( self, pkg ):
        ''' Just run pip install pkg '''
        from subprocess import check_call, PIPE
        check_call( ['pip', 'install', pkg] )

class bdist_egg(_bdist_egg):
    def run(self):
        self.run_command('install_pipeline')

class develop(_develop):
    def run(self):
        install_pipeline = self.distribution.get_command_obj('install_pipeline')
        install_pipeline.develop = True
        self.run_command('install_pipeline')
        _develop.run(self)

# Run setuptools setup
setup(
    name = "miseqpipeline",
    version = __version__,
    packages = find_packages(),
    scripts = glob('bin/*'),
    install_requires = [
        #'numpy==1.8.0',
        'PyVCF==0.6.6',
        'python-dateutil==2.1',
        'matplotlib==1.3.1',
        'biopython==1.63',
        'cutadapt==1.2.1',
        'nose',
        'mock',
        'pyBWA==v0.2.2',
        'tempdir',
    ],
    dependency_links = [
        'git+https://github.com/VDBWRAIR/pyBWA#egg=pyBWA-v0.2.2',
    ],
    setup_requires = [
        'tempdir'
    ],
    tests_require = [
    ],
    author = 'Tyghe Vallard',
    author_email = 'vallardt@gmail.com',
    description = 'Pipeline that combines sff and fastq files from multiple platforms',
    license = '',
    keywords = 'miseq iontorrent roche 454 fastq vcf',
    url = 'https://github.com/VDBWRAIR/miseqpipeline',
    cmdclass = {
        'install_system_packages': InstallSystemPackagesCommand,
        'install_pipeline': PipelineInstallCommand,
        'bdist_egg': PipelineInstallCommand,
        'develop': develop,
    },
)
