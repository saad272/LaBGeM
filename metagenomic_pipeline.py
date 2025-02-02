#! /env/cns/proj/agc/scratch/conda/miniconda3/bin/python

import os,sys,re
from Bio import SeqIO
import statistics
from collections import defaultdict
import argparse
import json
import shutil

def creatingDatatables(directory) :

    contigDb_filename =   directory+'/'+'contigs.db'
    profileDb_filename = directory+'/'+'anvio'+'/'+'PROFILE.db'

    datatable_dir = directory+'/'+'datatables'
    # if datatables isn't prensent, create it #
    if os.path.exists(datatable_dir) :
        shutil.rmtree(datatable_dir)
    os.mkdir(datatable_dir)

    taxo_anvio_filename = datatable_dir+'/'+'taxon_names.txt'
    if not os.path.exists(taxo_anvio_filename) :
        cmd = 'source activate anvio-6.2 && anvi-export-table '+contigDb_filename+' --table taxon_names -o '+taxo_anvio_filename+' >/dev/null 2>&1'
        print(cmd)
        status = os.system(cmd)
        print('status: '+str(status)+'\n')
        if not status == 0 :
            sys.exit('something went wrong with anvi-export-table, exit.')

    gene_taxo_anvio_filename = datatable_dir+'/'+'genes_taxonomy.txt'
    if not os.path.exists(gene_taxo_anvio_filename) :
        cmd = 'source activate anvio-6.2 && anvi-export-table '+contigDb_filename+' --table genes_taxonomy -o '+gene_taxo_anvio_filename+' >/dev/null 2>&1'
        print(cmd)
        status = os.system(cmd)
        print('status: '+str(status)+'\n')
        if not status == 0 :
            sys.exit('something went wrong with anvi-export-table, exit.')

    basic_info_contigs_filename = datatable_dir+'/'+'contigs_basic_info.txt'
    if not os.path.exists(basic_info_contigs_filename) :
        cmd = 'source activate anvio-6.2 && anvi-export-table '+contigDb_filename+' --table contigs_basic_info -o '+basic_info_contigs_filename+' >/dev/null 2>&1'
        print(cmd)
        status = os.system(cmd)
        print('status: '+str(status)+'\n')
        if not status == 0 :
            sys.exit('something went wrong with anvi-export-table, exit.')

    coverage_contigs_filename = datatable_dir+'/'+'contigs_coverage_info.txt'
    if not os.path.exists(coverage_contigs_filename) :
        cmd = 'source activate anvio-6.2 && anvi-export-splits-and-coverages -p '+profileDb_filename+' -c '+contigDb_filename+' -o '+datatable_dir+' -O '+'tmp'+' --report-contigs'+' >/dev/null 2>&1'
        print(cmd)
        status = os.system(cmd)
        print('status: '+str(status)+'\n')
        if not status == 0 :
            sys.exit('something went wrong with anvi-export-splits-and-coverages, exit.')
        os.rename(datatable_dir+'/'+'tmp-COVs.txt',coverage_contigs_filename)
        os.remove(datatable_dir+'/'+'tmp-CONTIGS.fa' )

    return coverage_contigs_filename,basic_info_contigs_filename,gene_taxo_anvio_filename,taxo_anvio_filename


def removingEukContigs(contig_filename,gene_call_filename,eukrep_euk_filename) :

    # running kaiju
    print()
    print('\tRunning Kaiju...')
    kaiju_filename = cwd+'/'+'taxonomy'+'/'+'all_kaiju.output'
    kaijuTaxon_filename = cwd+'/'+'taxonomy'+'/'+'all_kaiju-addTaxonNames.output'

    cmd = 'source activate metagenomics-v1 && kaiju -t /env/ig/biobank/by-soft/kaiju/1.7.3/i20200525/nodes.dmp -f /env/ig/biobank/by-soft/kaiju/1.7.3/i20200525/kaiju_db_nr_euk.fmi -i '+gene_call_filename+' -o '+kaiju_filename+' -z '+str(cpu)+' -v'
    print('\t'+cmd)
    status = os.system(cmd)
    print('\t'+'status :'+str(status))
    if not status == 0:
        sys.exit('something went wrong with kaiju, exit')

    cmd = 'source activate metagenomics-v1 && kaiju-addTaxonNames -t /env/ig/biobank/by-soft/kaiju/1.7.3/i20200525/nodes.dmp -n /env/ig/biobank/by-soft/kaiju/1.7.3/i20200525/names.dmp -i '+kaiju_filename+' -o '+kaijuTaxon_filename+' -r superkingdom,phylum,order,class,family,genus,species'+' -v'
    print('\t'+cmd)
    status = os.system(cmd)
    print('\t'+'status :'+str(status))
    if not status == 0:
        sys.exit('something went wrong with kaiju-addTaxonNames, exit')

    kaijuContigSet = set()
    file = open(kaijuTaxon_filename,'r')
    for line in file :
        line  = line.rstrip()
        liste = line.split('\t')
        if liste[0] == 'C' :
            lineage = liste[-1]
            lineageList = lineage.split(';')
            domain = lineageList[0].strip()
            if domain == 'Eukaryota' :
                kaijuContigSet.add(liste[1])
            else:
                continue
        else:
            continue
    file.close()
    print('\t'+'Number of eukaryotic genes according to Kaiju: '+str(len(kaijuContigSet)))

    eukRepContigSet = set()
    file = open(eukrep_euk_filename,'r')
    for line in file :
        contig = line.rstrip()
        eukRepContigSet.add(contig)
    file.close()
    print('\t'+'Number of eukaryotic contigs according to EukRep: '+str(len(eukRepContigSet)))
    #print('\t'+'Number of eukaryotic contigs according to both Kaiju and EukRep: '+str(len(kaijuContigSet.intersection(eukRepContigSet))))

    return eukRepContigSet


def renamingContigs(contig_filename,renamed_contig_filename,project,sample) :
    output = open(renamed_contig_filename,'w')
    file = open(contig_filename,'r')
    for line in file :
        line = line.rstrip()
        if re.match('>',line) :
            header = line.split()[0][1:]
            defline = project+'__'+sample+'__'+header
            output.write('>'+defline+'\n')
        else:
            output.write(line+'\n')
    file.close()
    output.close()



def extractingBam(bam_filename,contig_filename,final_bam_filename,fake_bam_filename,cpu):
    # creating the bed file
    contigSet = set()
    for record in SeqIO.parse(contig_filename,'fasta') :
        contigSet.add(record.id)

    # converting the bam to a sam file
    tmp_sam_filename = bam_filename+'.tmp.sam'
    cmd = 'source activate metagenomics-v1 &&  samtools view -h '+bam_filename+' -o '+tmp_sam_filename
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status)+'\n')
    if not status == 0 :
        sys.exit('something went wrong with samtools view, exit')

    tmp_filename = bam_filename+'.tmp.shorter.sam'
    output = open(tmp_filename,'w')
    file = open(tmp_sam_filename,'r')
    for line in file :
        line = line.rstrip()
        liste = line.split('\t')
        if re.match(r'@SQ',line) :
            contig = liste[1].replace('SN:','')
            if contig in contigSet :
                output.write(line+'\n')
            else:
                continue
        elif re.match(r'@',line) :
            output.write(line+'\n')
        else:
            contig = liste[2]
            if contig in contigSet :
                output.write(line+'\n')
            else:
                continue
    output.close()
    file.close()

    # removing the tmp file
    os.remove(tmp_sam_filename)


    # creating and sorting a bam file 
    cmd = 'source activate metagenomics-v1 && samtools view -Sb '+' '+tmp_filename+' | samtools sort -@ '+str(cpu)+' -o'+final_bam_filename
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status)+'\n')
    if not status == 0 :
        sys.exit('something went wrong with samtools sort, exit.')

    # removing the tmp file
    os.remove(tmp_filename)

    # creating the index file
    cmd = 'source activate metagenomics-v1 && samtools index '+final_bam_filename
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status)+'\n')
    if not status == 0 :
        sys.exit('something went wrong with samtools index, exit.')

    # creating a fake bam to allow the coverage sorting in ANVIO
    os.symlink(final_bam_filename, fake_bam_filename)
    os.symlink(final_bam_filename+'.bai', fake_bam_filename+'.bai')



def parsingProdigal(protein_filename,output_filename,contig_filename) :
    contigList = set()
    for record in SeqIO.parse(contig_filename,'fasta') :
        contigList.add(record.id)


    cpt = 0
    output = open(output_filename,'w')
    header = 'gene_callers_id'+'\t'+'contig'+'\t'+'start'+'\t'+'stop'+'\t'+'direction'+'\t'+'partial'+'\t'+'source'+'\t'+'version'+'\t'+'aa_sequence'
    output.write(header+'\n')
    for record in SeqIO.parse(protein_filename,'fasta') :
        liste = record.description.split(' # ')
        orf = str(cpt)
        cpt += 1
        scaffold = '_'.join(liste[0].split('_')[0:-1])
        if scaffold not in contigList :
            continue

        start = str( int(liste[1]) - 1 )
        end = str( int(liste[2]) - 1 )
        if int( liste[-1].split(';')[1].replace('partial=','') ) == 0 :
            partial = '0'
        else:
            partial = '1'

        if liste[3] == '1' :
            strand = 'f'
        else:
            strand = 'r'
        line = orf+'\t'+scaffold+'\t'+start+'\t'+end+'\t'+strand+'\t'+partial+'\t'+'prodigal'+'\t'+'2.6.3'+'\t'+str(record.seq)
        output.write(line+'\n')
    output.close()


def parsingEukRep(euk_filename,prok_filename,contig2split) :
    contig2orig = dict()
    file = open(euk_filename,'r')
    for line in file :
        contig = line.rstrip()
        for split in contig2split[contig] :
            contig2orig[split] = 'EUK'
    file.close()

    file = open(prok_filename,'r')
    for line in file :
        contig = line.rstrip()
        for split in contig2split[contig] :
            contig2orig[split] = 'PROK'
    file.close()
    
    
    for contig,liste in contig2split.items() :
        for split in liste:
            if split not in contig2orig :
                contig2orig[split] = 'UNK'
            else:
                continue

    return contig2orig


def additionalDataTable(annot2data,output_filename,splitList) :

    output = open(output_filename,'w')
    
    categoryList = sorted(list(annot2data.keys()))
    output.write('item_name'+'\t'+'\t'.join( categoryList )+'\n')

    for contig in splitList :
        line = contig
        for category in categoryList :
            result = str(annot2data[category][contig])
            line += '\t'+result
        line += '\n'
        output.write(line)
    output.close()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Run the metagenomic pipeline')
    parser.add_argument('-fq1', help='the path of the first FASTQ_FILENAME that contains the reads')
    parser.add_argument('-fq2', help='the path of the second FASTQ_FILENAME that contains the reads')
    parser.add_argument('-cwd', help='the path to the working directory where the assembly folder will be created')
    parser.add_argument('-project', help='the name of the project that will be prefixed in the contig names')
    parser.add_argument('-sample', help='the name of the project that will be prefixed in the contig names')
    parser.add_argument('-cpu',type=int,default=1,help='number of CPUs used by hhblits (default: 1)')
    parser.add_argument('-k',type=int,default=25000,help='number of contigs to keep for ANVIO (default: 25000)')
    parser.add_argument('-remove-euk',action='store_true',default=False,help='remove the contigs assigned to euk by both kaiju and EukRep')
    args = parser.parse_args()

    # checking arguments

    if args.fq1 == None or args.fq2 == None or args.cwd == None or args.project == None or args.sample == None :
        sys.exit('fq1, fq2, cwd, project and sample are mandatory parameters')

    if not os.path.exists(args.fq1) or not os.path.exists(args.fq2) :
        sys.exit(args.fq1+' or '+args.fq2+' does not exist, exit')
    elif args.fq1 == args.fq2 :
        sys.exit(' fq1 and fq2 are identical, exit')
    else:
        fastq1_filename = os.path.abspath(args.fq1)
        fastq2_filename = os.path.abspath(args.fq2)

    if not os.path.exists(args.cwd) :
        sys.exit(cwd+' does not exist')
    else:
        cwd = os.path.abspath(args.cwd+'/'+'assembly')

    if args.cpu < 1 :
        cpu = 1
    else:
        cpu = args.cpu

    if args.k < 1 :
        k = 25000
    else:
        k = args.k

    noFunkyCharacter = r'^[A-Za-z0-9_]*$'
    if re.match(noFunkyCharacter, args.sample) and re.match(noFunkyCharacter, args.project) :
        sample = args.sample
        project = args.project
    else:
        print(sample)
        print(project)
        sys.exit('Please limit the characters that make up the project and sample names to ASCII letters, digits, and the underscore character')


    right = 0o0666

    print('\n')
    print('##############')
    print('# parameters #')
    print('##############')
    print()
    print('Project name: '+project)
    print('Sample name: '+sample)
    print('Working directory: '+cwd)
    print('Fastq1: '+fastq1_filename)
    print('Fastq2: '+fastq2_filename)
    print('Number of CPUs: '+str(cpu))
    print('Number of contigs to consider for ANVIO: '+str(k))
    print('Removing eukaryotic contigs: '+str(args.remove_euk))


    print('\n')
    print('############')
    print('# pipeline #')
    print('############')
    print()

    #############
    # json data #
    #############

    json_data = dict()
    json_data['project'] = project
    json_data['sample'] = sample
    json_data['directory'] = args.cwd
    json_data['assembly_directory'] = cwd
    json_data['assembly_cmd_line'] = ' '.join(sys.argv)


    ##############################
    # creating the cwd directory #
    ##############################

    print('checking if '+cwd+' directory exists...')
    if os.path.exists(cwd) :
        print(cwd+' already exists, trying to clean up the directory in order to keep the assembly and bowtie mapping...')
        for root, dirs, files in os.walk(cwd):            
            for filename in files :
                if re.search(r'^megahit.contigs',filename) :
                    if root != cwd :
                        print(root)
                        continue
                    if filename == 'megahit.contigs.renamed.fa' :
                        continue
                    if filename == 'megahit.contigs.fa' :
                        continue
                    print('removing '+root+'/'+filename+'...')
                    os.remove(root+'/'+filename)

    print('done\n')

    #################
    # megahit 1.2.9 #
    #################

    contig_filename = cwd+'/'+'megahit.contigs.fa'
    print('\n')
    print('Performing the assembly using  megahit...') # megahit will create a directory named assembly
    if os.path.exists(contig_filename) and os.path.exists(cwd+'/'+'done') :
        print(contig_filename+' already exists and looks good, keep it')        
    else:
        cmd = 'source activate metagenomics-v1 && megahit -1 '+fastq1_filename+' -2 '+fastq2_filename+' -o '+cwd+' --out-prefix megahit --num-cpu-threads '+str(cpu)   ### 1 paired-end library --mem-flag 0
        print(cmd)
        status = os.system(cmd)
        print(status)
        if status != 0 :
            sys.exit('something went wrong with megahit, exit')
        print('\n')
    print('done')


    ########################
    # renaming the contigs #
    ########################

    print('\n')
    print('Renaming the contigs...')
    renamed_contig_filename = cwd+'/'+'megahit.contigs.renamed.fa'
    json_data['assembly_contig_filename'] = renamed_contig_filename
    if os.path.exists(renamed_contig_filename) and os.path.exists(contig_filename) and os.path.exists(cwd+'/'+'done') :
        print(contig_filename+' already exists and looks good, keep '+renamed_contig_filename+' as it is')
    else:
        renamingContigs(contig_filename,renamed_contig_filename,project,sample) # renaming the contigs + checking for funky characters
    print('done')


    ###########
    # idba-ud #
    ###########

    # print('\n')
    # print('Performing the scaffolding using IDBA-UD...')
    # cmd = 'scaffold '+contig_filename+' '+fastq1_filename+' '+fastq2_filename+' -seed_kmer 100 -min_contig 1000 -o '+cwd
    # print(cmd)
    # print('done')



    #######################
    # mapping with bowtie #
    #######################

    print('\n')
    print('Performing coverage profiling using bowtie2...')
    basename = os.path.basename(renamed_contig_filename)
    bam_filename = cwd+'/'+'bt2'+'/'+basename+'.bam'

    json_data['assembly_bam_filename'] = bam_filename
    json_data['assembly_bai_filename'] = bam_filename+'.bai'


    if os.path.exists(bam_filename+'.bai') and os.path.exists(bam_filename) and  os.path.exists(renamed_contig_filename) and os.path.exists(contig_filename) and os.path.exists(cwd+'/'+'done') :
        print(contig_filename+' and '+renamed_contig_filename+' already exist and look good, keep '+bam_filename+'.bai and '+bam_filename+' as they are')
        for root, dirs, files in os.walk(cwd+'/'+'bt2'):
            for filename in files :
                if root+'/'+filename == bam_filename :
                    print('\t'+root+'/'+filename+' already exists, keep it')
                    continue

                if root+'/'+filename == bam_filename+'.bai' :
                    print('\t'+root+'/'+filename+' already exists, keep it')
                    continue

                os.remove(root+'/'+filename)
        if not os.path.exists(bam_filename+'.bai') or not os.path.exists(bam_filename) :
            sys.exit('something went wrong when cleaning the bt2 folder, exit')

    else:
        if os.path.exists(cwd+'/'+'bt2') :
            shutil.rmtree(cwd+'/'+'bt2')
        os.mkdir(cwd+'/'+'bt2')

        print(bam_filename)
        cmd = 'source activate metagenomics-v1 && bowtie2-build --threads '+str(cpu)+' '+renamed_contig_filename+' '+cwd+'/'+'bt2'+'/'+basename
        print(cmd)
        status = os.system(cmd)
        print(status)
        if not status == 0:
            sys.exit('something went wrong with bowtie2-build, exit')

        cmd = 'source activate metagenomics-v1 && bowtie2 -p '+str(cpu)+' -X 1000 -x '+cwd+'/'+'bt2'+'/'+basename+' -1 '+fastq1_filename+' -2 '+fastq2_filename +' | '+'samtools view -Sb'+' | '+'samtools sort -@ '+str(cpu)+' -o '+bam_filename
        print(cmd)
        status = os.system(cmd)
        print(status)
        if not status == 0:
            sys.exit('something went wrong with bowtie2, exit')

        # creating the index file
        cmd = 'source activate metagenomics-v1 && samtools index '+bam_filename
        print(cmd)
        status = os.system(cmd)
        print('status: '+str(status)+'\n')
        if not status == 0 :
            sys.exit('something went wrong with samtools index, exit.')
    print('done')


    ############
    # prodigal #
    ############

    print('\n')
    print('Performing the gene prediction using prodigal...')
    protein_filename = cwd+'/'+'proteins.faa'
    gene_filename = cwd+'/'+'genes.fna'

    json_data['assembly_protein_filename'] = protein_filename
    json_data['assembly_gene_filename'] = gene_filename

    cmd = 'source activate metagenomics-v1 && prodigal -i '+renamed_contig_filename+' -a '+protein_filename+' -d '+gene_filename+' -m -p meta >/dev/null 2>/dev/null'
    print(cmd)
    status = os.system(cmd)
    print(status)
    if not status == 0:
        sys.exit('something went wrong with prodigal, exit')
    print('done')



    ######################
    # adding annotations #
    ######################

    if os.path.exists(cwd+'/'+'annotations') :
        shutil.rmtree(cwd+'/'+'annotations')

    os.mkdir(cwd+'/'+'annotations')

    # running eukRep
    print('\n')
    print('Adding annotations...')
    print()
    print('\trunning EukRep...')
    eukrep_prok_filename = cwd+'/'+'annotations'+'/'+'eukrepProk.txt'
    eukrep_euk_filename = cwd+'/'+'annotations'+'/'+'eukrepEuk.txt'
    cmd = 'source activate metagenomics-v1 && EukRep -i '+renamed_contig_filename+' -o '+eukrep_euk_filename+' --prokarya '+eukrep_prok_filename+' --seq_names -m strict --tie skip' 
    print(cmd)
    status = os.system(cmd)
    print('status :'+str(status))
    if not status == 0:
        sys.exit('something went wrong with EukRep.py, exit')
    print('\tdone')

    print('done')




    #############################################
    # Selecting the contigs to display in ANVIO #
    #############################################

    print('\n')
    print('Selecting the '+str(k)+' longest contigs and the contigs longer than 1000bp...')


    if args.remove_euk : # removing the euk contigs from the bining step
        print('\tRemoving eukaryotic contigs and perfomrming kaiju taxonomy')

        if os.path.exists(cwd+'/'+'taxonomy') :
            shutil.rmtree(cwd+'/'+'taxonomy')
        os.mkdir(cwd+'/'+'taxonomy')

        eukContigSet = removingEukContigs(contig_filename,gene_filename,eukrep_euk_filename)
        print('\tDone')
    else:
        eukContigSet = set()


    lengthList = list()
    for record in SeqIO.parse(renamed_contig_filename,'fasta') :
        if record.id in eukContigSet :
            continue
        else :
            lengthList.append(len(record))

    print('\tTotal number of contigs: '+str(len(lengthList)))
    print('\tMedian length: '+str(statistics.median(lengthList)))

    contigSet = set()
    liste = list()
    cpt = 1
    CPT = 1
    for length in sorted(lengthList,reverse=True) :
        #print(str(cpt)+'\t'+str(length))
        if length > 2900 :
            CPT += 1

        if length < 1000 or cpt > k :
            continue
        else:
            cpt += 1
            liste.append(length)

    cpt = cpt - 1 
    length = sorted(lengthList,reverse=True)[cpt - 1]

    print('\tLength of '+str(cpt)+'th longuest contig: '+str(length))
    print('\tMedian length of the '+str(cpt)+' longuest contigs: '+str(statistics.median(liste)))
    print('\tNumber of contigs > 2900: '+str(CPT-1)+' ('+str(sorted(lengthList,reverse=True)[CPT - 1])+')')

    if args.remove_euk :
        contig_filename = cwd+'/'+'megahit.contigs.renamed'+'.noEuk.min'+str(length)+'.fa'
    else:
        contig_filename = cwd+'/'+'megahit.contigs.renamed'+'.min'+str(length)+'.fa'

    json_data['anvio_contig_filename'] = contig_filename

    output = open(contig_filename,'w')
    for record in SeqIO.parse(renamed_contig_filename,'fasta') :
        if record.id in eukContigSet :
            continue
        else:
            if len(record) >= length :
                SeqIO.write(record,output,'fasta')
                liste.append(len(record))
            else:
                continue
    output.close()
    print('done')




    ####################################################
    # filtering out, indexing and sorting the filename #
    ####################################################

    print('\n')
    print('Filtering out, indexing and sorting the filename...')
    if args.remove_euk :
        final_bam_filename = cwd+'/'+'bt2'+'/'+basename+'.noEuk.min'+str(length)+'.sorted.bam'
        fake_bam_filename =  cwd+'/'+'bt2'+'/'+basename+'.noEuk.min'+str(length)+'.sorted.fake.bam'
    else:
        final_bam_filename = cwd+'/'+'bt2'+'/'+basename+'.min'+str(length)+'.sorted.bam'
        fake_bam_filename =  cwd+'/'+'bt2'+'/'+basename+'.min'+str(length)+'.sorted.fake.bam'


    extractingBam(bam_filename,contig_filename,final_bam_filename,fake_bam_filename,cpu)
    print('done')

    bam2name = dict()
    bam2name[fake_bam_filename] = 'fake_profile'
    bam2name[final_bam_filename] = 'genuine_profile'

    json_data['anvio_bam_filename'] = final_bam_filename
    json_data['anvio_bai_filename'] = final_bam_filename+'.bai'

    ###################################
    # creating protein file for ANVIO #
    ###################################

    print('\n')
    print('Creating the protein file for ANVIO...')
    protein_anvio_filename = cwd+'/'+'proteins.anvio.tab'
    parsingProdigal(protein_filename,protein_anvio_filename,contig_filename) #only on the k contigs
    print('done')

    json_data['anvio_protein_filename'] = protein_anvio_filename

    print('\ngreat, you have completed the first (and longest) part of the pipeline, now let\'s run the anvio\'s commands')



    #########################
    #########################
    #### ANVIO CMD LINES ####
    #########################
    #########################


    #######################################
    # Creating an anvi’o contigs database # http://merenlab.org/2016/06/22/anvio-tutorial-v2/#creating-an-anvio-contigs-database
    #######################################

    print('\n\nCreating the contig.db file')
    contig_db_filename = cwd+'/'+'contigs.db'
    json_data['anvio_contigDb_filename'] = contig_db_filename
    cmd = 'source activate anvio-6.2 && anvi-gen-contigs-database -f '+contig_filename+' -o '+contig_db_filename+' -n '+'\'The contigs database\''+' --external-gene-calls '+protein_anvio_filename
    print(cmd)
    status = os.system(cmd)
    print(status)
    if not status == 0:
        sys.exit('something went wrong with anvi-gen-contigs-database, exit')

    cmd = 'source activate anvio-6.2 && anvi-run-hmms -c '+contig_db_filename+' -T '+str(cpu)
    print(cmd)
    status = os.system(cmd)
    print(status)
    if not status == 0:
        sys.exit('something went wrong with anvi-run-hmms, exit')

    os.chmod(contig_db_filename, right )
    print('done')



    ##############################################
    # Importing the items data tables into ANVIO #
    ##############################################

    # anvi-[import|export|show|delete]-misc-data # import annotations
    print('\n')
    print('Importing the annotations into ANVIO...')

    cmd = 'source activate anvio-6.2 && anvi-export-table '+contig_db_filename+' --table genes_in_splits -o '+cwd+'/'+'genes_in_splits.txt'
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status))
    if not status == 0:
        sys.exit('something went wrong with anvi-export-table, exit')

    splitList = set()
    contig2split = defaultdict(set)
    file = open(cwd+'/'+'genes_in_splits.txt','r')
    header = next(file)
    for line in file :
        line = line.rstrip()
        liste = line.split('\t')
        split = liste[1]
        contig = '_'.join( split.split('_')[:-2] )
        splitList.add(split)
        contig2split[contig].add(split)
    file.close()

    contig2eukrep = parsingEukRep(eukrep_euk_filename,eukrep_prok_filename,contig2split)

    items_filename = cwd+'/'+'annotations'+'/'+'items_additional_data.txt'
    annot2data = {'EukRep' : contig2eukrep}

    additionalDataTable(annot2data,items_filename,splitList)
    print('done')


    ########################
    # anvi-import-taxonomy #
    ########################

    # running kaiju
    print()
    print('Running Kaiju...')

    if os.path.exists(cwd+'/'+'taxonomy') :
        shutil.rmtree(cwd+'/'+'taxonomy')
    os.mkdir(cwd+'/'+'taxonomy')


    gene_call_filename = cwd+'/'+'gene-calls.fa'
    kaiju_filename = cwd+'/'+'taxonomy'+'/'+'kaiju.output'
    kaijuTaxon_filename = cwd+'/'+'taxonomy'+'/'+'kaiju-addTaxonNames.output'

    cmd = 'source activate anvio-6.2 && anvi-get-sequences-for-gene-calls -c '+contig_db_filename+' -o '+gene_call_filename
    print(cmd)
    status = os.system(cmd)
    print('status :'+str(status))
    if not status == 0:
        sys.exit('something went wrong with anvi-get-sequences-for-gene-calls, exit')

    cmd = 'source activate metagenomics-v1 && kaiju -t /env/ig/biobank/by-soft/kaiju/1.7.3/i20200525/nodes.dmp -f /env/ig/biobank/by-soft/kaiju/1.7.3/i20200525/kaiju_db_nr_euk.fmi -i '+gene_call_filename+' -o '+kaiju_filename+' -z '+str(cpu)+' -v'
    print(cmd)
    status = os.system(cmd)
    print('status :'+str(status))
    if not status == 0:
        sys.exit('something went wrong with kaiju, exit')

    cmd = 'source activate metagenomics-v1 && kaiju-addTaxonNames -t /env/ig/biobank/by-soft/kaiju/1.7.3/i20200525/nodes.dmp -n /env/ig/biobank/by-soft/kaiju/1.7.3/i20200525/names.dmp -i '+kaiju_filename+' -o '+kaijuTaxon_filename+' -r superkingdom,phylum,order,class,family,genus,species'+' -v'
    print(cmd)
    status = os.system(cmd)
    print('status :'+str(status))
    if not status == 0:
        sys.exit('something went wrong with kaiju-addTaxonNames, exit')



    cmd = 'source activate anvio-6.2 && anvi-import-taxonomy-for-genes -i '+kaijuTaxon_filename+' -c '+contig_db_filename+' -p kaiju --just-do-it'
    print(cmd)
    status = os.system(cmd)
    print('status :'+str(status))
    if not status == 0:
        sys.exit('something went wrong with anvi-import-taxonomy-for-genes, exit')
    print('done')





    ############################
    # Creating the profiles DB #
    ############################

    print()
    print('Running anvi-profile...')

    if os.path.exists(cwd+'/'+'profiles') :
        shutil.rmtree(cwd+'/'+'profiles')

    os.mkdir(cwd+'/'+'profiles')
    os.mkdir(cwd+'/'+'profiles'+'/'+'fake_profile')
    os.mkdir(cwd+'/'+'profiles'+'/'+'genuine_profile')

    profileList = list()
    for bam_filename,name in sorted( bam2name.items() ) :
        profile_filename = cwd+'/'+'profiles'+'/'+name+'/'+'PROFILE.db'
        auxiliaryData_filename = cwd+'/'+'profiles'+'/'+name+'/'+'AUXILIARY-DATA.db'
        profileList.append(profile_filename)
        cmd = 'source activate anvio-6.2 && anvi-profile -i '+bam_filename+' -c '+contig_db_filename+' --sample-name \''+name+'\' --output-dir '+cwd+'/'+'profiles'+'/'+name+' --overwrite-output-destinations -T '+str(cpu)
        print(cmd)
        status = os.system(cmd)
        print('status: '+str(status))
        if not status == 0:
            sys.exit('something went wrong with anvi-profile, exit')
        os.chmod(profile_filename, right )
        os.chmod(auxiliaryData_filename, right )
    print('done')



    ###############
    # anvio merge #
    ###############

    profile_filename = cwd+'/'+'anvio'+'/'+'PROFILE.db'
    json_data['anvio_profileDb_filename'] = profile_filename
    cmd = 'source activate anvio-6.2 && anvi-merge '+' '.join(profileList)+' -o '+cwd+'/'+'anvio'+' -c '+contig_db_filename+' --sample-name \''+project+'__'+sample+'\' --overwrite-output-destinations --enforce-hierarchical-clustering'
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status))
    if not status == 0:
        sys.exit('something went wrong with anvi-merge, exit')
    print('\n\n')

    cmd = 'source activate anvio-6.2 && anvi-import-misc-data '+items_filename+' -p '+profile_filename+' --target-data-table items'
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status))
    if not status == 0:
        sys.exit('something went wrong with anvi-import-misc-data, exit')


    ###########################
    # creating the datatables #
    ###########################    
    print('\nExporting the datatables...\n')
    coverage_contigs_filename,basic_info_contigs_filename,gene_taxo_anvio_filename,taxo_anvio_filename = creatingDatatables(cwd)
    json_data['anvio_coverage_contigs_filename'] = coverage_contigs_filename
    json_data['anvio_basic_info_contigs_filename'] = basic_info_contigs_filename
    json_data['anvio_gene_taxo_anvio_filename'] = gene_taxo_anvio_filename
    json_data['anvio_taxo_filename'] = taxo_anvio_filename

    print('done\n')


    #########################
    # creating the json file #
    #########################
    
    json_filename = cwd+'/'+'info.json'
    output = open(json_filename, "w")
    json.dump( json_data, output, sort_keys=True, indent=4 )
    output.write('\n')
    output.close()

    auxiliaryData_filename = cwd+'/'+'anvio'+'/'+'AUXILIARY-DATA.db'
    os.chmod(profile_filename, right )
    os.chmod(auxiliaryData_filename, right )


    #####################
    # anvio interactive #
    #####################

    print('\nLaunch the ANVIO web interface please run the following commands:\n')
    cmd = 'conda activate anvio-6.2'
    print(cmd)
    cmd = 'anvi-interactive --server-only -p '+profile_filename+' -c '+contig_db_filename
    print(cmd)
    sys.exit()


