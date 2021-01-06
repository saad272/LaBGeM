#! /usr/bin/python3

import os,sys,re
from collections import defaultdict


def gettingContigInfo(basic_info_contigs_filename, coverage_contigs_filename ) : # minimum percentage of genes to assign a scaffold to a taxonomic group (default: 20.0)
    scaffold2info  = defaultdict()
    file = open( basic_info_contigs_filename, 'r' )
    header = next(file)
    for line in file :
        line = line.rstrip()
        scaffold,length,gc,nb_splits = line.split('\t')
        scaffold2info[ scaffold ] = [length,gc,nb_splits]
    file.close()

    file = open( coverage_contigs_filename, 'r' )
    header = next(file)
    for line in file :
        line = line.rstrip()
        scaffold,coverage = line.split('\t')
        scaffold2info[ scaffold ].append(coverage)
    file.close()
    
    return scaffold2info


def detectingContigTaxonomy(gene_taxo_anvio_filename , taxo_anvio_filename , protein_filename ) : # minimum percentage of genes to assign a scaffold to a taxonomic group (default: 20.0)

    scaffold2genes = defaultdict(set)
    gene2scaffold = dict()
    file = open( protein_filename, 'r' )
    header = next(file)
    for line in file :
        line = line.rstrip()
        liste = line.split('\t')
        geneId = liste[0]
        scaffold = liste[1]
        gene2scaffold[ geneId ] = scaffold
        scaffold2genes[ scaffold ].add(geneId)
    file.close()

    taxoId2taxon = dict()
    file = open( taxo_anvio_filename, 'r' )
    header = next(file)
    for line in file :
        line = line.rstrip()
        liste = line.split('\t')
        taxoId = liste[0]
        del liste[0]
        taxoId2taxon[taxoId] = liste
    file.close()

    geneId2taxoId = dict()
    file = open( gene_taxo_anvio_filename, 'r' )
    header = next(file)
    for line in file :
        line = line.rstrip()
        geneId,taxoId = line.split('\t')
        geneId2taxoId[ geneId ] = taxoId
    file.close()

    scaffold2taxonomy = dict()
    for scaffold,geneSet in scaffold2genes.items() :
        #print()
        #print(scaffold)
        taxo2pct = defaultdict(float)
        for geneId in sorted(geneSet) :
            if geneId in geneId2taxoId :
                taxoId = geneId2taxoId[ geneId ]
                taxon = taxoId2taxon[taxoId][-2]
            else:
                taxon = 'Unknown'

            #print('\t'+geneId+'\t'+str(taxon) )
            taxo2pct[ taxon ] += 1 / float(len(geneSet))
        #print('\t'+str(taxo2pct))
        #print()

        TAXON = ''
        for taxon,pct in sorted(taxo2pct.items(),key=lambda x:x[1], reverse=True) :
            #print('\t\t'+taxon+'\t'+str(pct))
            if pct > 0.2 and taxon != 'Unknown' :
                if TAXON == '' :
                    TAXON = taxon

        if TAXON != '' :
            #print('\t\ttaxon: '+TAXON)
            scaffold2taxonomy[ scaffold ] = TAXON

    return scaffold2taxonomy


collection = 'raphael_1_20201108'
directory = '/env/cns/proj/projet_CSD/scratch/assemblies/Ecro_F_AB1'

profileDb_filename = directory+'/'+'assembly'+'/'+'anvio'+'/'+'PROFILE.db'
contigDb_filename =  directory+'/'+'assembly'+'/'+'contigs.db'
scaffold_filename =  directory+'/'+'assembly'+'/'+'megahit.contigs.renamed.fa'
protein_filename =   directory+'/'+'assembly'+'/'+'proteins.anvio.tab'
bam_filename = directory+'/'+'assembly'+'/'+'bt2'+'/'+'megahit.contigs.renamed.fa.bam'
bai_filename = directory+'/'+'assembly'+'/'+'bt2'+'/'+'megahit.contigs.renamed.fa.bam.bai'
cpu = str(36)



datatable_dir = directory+'/'+'assembly'+'/'+'datatables'
# if datatables isn't prensent, create it #
if not os.path.exists(datatable_dir) :
    os.mkdir(datatable_dir)


taxo_anvio_filename = datatable_dir+'/'+'taxon_names.txt'
if not os.path.exists(taxo_anvio_filename) :
    cmd = 'source activate anvio-6.2 && anvi-export-table '+contigDb_filename+' --table taxon_names -o '+taxo_anvio_filename
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status)+'\n')
    if not status == 0 :
        sys.exit('something went wrong with anvi-export-table, exit.')


gene_taxo_anvio_filename = datatable_dir+'/'+'genes_taxonomy.txt'
if not os.path.exists(gene_taxo_anvio_filename) :
    cmd = 'source activate anvio-6.2 && anvi-export-table '+contigDb_filename+' --table taxon_names -o '+gene_taxo_anvio_filename
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status)+'\n')
    if not status == 0 :
        sys.exit('something went wrong with anvi-export-table, exit.')


basic_info_contigs_filename = datatable_dir+'/'+'contigs_basic_info.txt'
if not os.path.exists(basic_info_contigs_filename) :
    cmd = 'source activate anvio-6.2 && anvi-export-table '+contigDb_filename+' --table contigs_basic_info -o '+basic_info_contigs_filename
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status)+'\n')
    if not status == 0 :
        sys.exit('something went wrong with anvi-export-table, exit.')


coverage_contigs_filename = datatable_dir+'/'+'contigs_coverage_info.txt'
if not os.path.exists(coverage_contigs_filename) :
    cmd = 'source activate anvio-6.2 && anvi-export-splits-and-coverages -p '+profileDb_filename+' -c '+contigDb_filename+' -o '+datatable_dir+' -O '+coverage_contigs_filename+' --report-contigs'
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status)+'\n')
    if not status == 0 :
        sys.exit('something went wrong with anvi-export-splits-and-coverages, exit.')


#scaffold2taxonomy = detectingContigTaxonomy(gene_taxo_anvio_filename , taxo_anvio_filename , protein_filename )


# if the bam_filename isn't sorted, do #
if not os.path.exists(bai_filename) :
    tmp_bam_filename = bam_filename+'.unsorted'
    os.rename(bam_filename,tmp_bam_filename)
    cmd = 'samtools sort -@ '+str(cpu)+' -o '+bam_filename+' -O BAM '+tmp_bam_filename
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status))

    # creating the index file
    cmd = 'samtools index '+bam_filename
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status)+'\n')
    if not status == 0 :
        sys.exit('something went wrong with samtools index, exit.')


    os.remove(tmp_bam_filename)
    if os.path.exists(tmp_bam_filename) :
        sys.exit('something went wrong with os.remove, exit')

    if not os.path.exists(bai_filename):
        sys.exit('something went wrong with samtools sort, exit')



refiningBins_directory = directory+'/'+'refinedBins'
if os.path.exists(refiningBins_directory) :
    print(refiningBins_directory+' already exist, please remove it first')
    sys.exit(refiningBins_directory+' already exist, please remove it first')
os.mkdir(refiningBins_directory)



#########
# ANVIO #
#########

anvio_directory = directory+'/'+'refinedBins'+'/'+'ANVIO'
if os.path.exists(anvio_directory) :
    sys.exit(anvio_directory+' already exist, please remove it first')
else:
    os.mkdir(anvio_directory)
    anvi_summarize_directory = anvio_directory+'/'+'SAMPLES-SUMMARY'
    cmd = 'source activate anvio-6.2 && anvi-summarize -p '+profileDb_filename+' -c '+contigDb_filename+' -o '+anvi_summarize_directory+' -C '+collection
    print(cmd)
    status = os.system(cmd)
    print('status: '+str(status))
    if not status == 0:
        sys.exit('something went wrong with anvi-summarize, exit')
        
    # ADD A FILE WITH THE COLLECTIONS NAME
    output = open(anvio_directory+'/'+'collection.txt','w')
    output.write(collection+'\n')
    output.close()


bin_dir = anvio_directory+'/'+'bins'
if os.path.exists(bin_dir) :
    sys.exit(bin_dir+' already exist, please remove it first')
os.mkdir(bin_dir)

print(bin_dir)
for root, dirs, files in os.walk(anvi_summarize_directory+'/'+'bin_by_bin', topdown = False):
    for binName in dirs:
        if re.match(r'Euk',binName) :
            continue
        fasta_filename = anvi_summarize_directory+'/'+'bin_by_bin'+'/'+binName+'/'+binName+'-contigs.fa'
        if not os.path.exists(bin_dir+'/'+binName+'.fna') :
            print(binName+'\t'+fasta_filename)
            os.symlink(fasta_filename,bin_dir+'/'+binName+'.fna')



###########
# refineM #
###########


# Removing contamination based on taxonomic assignments


refineM_dir = refiningBins_directory+'/'+'refineM'
if os.path.exists(refineM_dir) :
    sys.exit(refineM_dir+' already exist, please remove it first')
os.mkdir(refineM_dir)

genomic_dir = refineM_dir+'/'+'genomicProperties'
if os.path.exists(genomic_dir) :
    sys.exit(genomic_dir+' already exist, please remove it first')
os.mkdir(genomic_dir)


stat_dir = genomic_dir+'/'+'stats'
if os.path.exists(stat_dir) :
    sys.exit(stat_dir+' already exist, please remove it first')
os.mkdir(stat_dir)


cmd = 'source activate refineM-0.1.2 && refinem scaffold_stats -c '+cpu+' '+scaffold_filename+' '+bin_dir+' '+stat_dir+' '+bam_filename
print(cmd)
status = os.system(cmd)
print('status: '+str(status))
if not os.path.exists(stat_dir+'/scaffold_stats.tsv'):
    sys.exit('something went wrong with refinem scaffold_stats, exit')


outliers_dir = genomic_dir+'/'+'outliers'
if os.path.exists(outliers_dir) :
    sys.exit(outliers_dir+' already exist, please remove it first')
os.mkdir(outliers_dir)

cmd = 'source activate refineM-0.1.2 && refinem outliers '+stat_dir+'/scaffold_stats.tsv'+' '+outliers_dir
print(cmd)
status = os.system(cmd)
print('status: '+str(status))
if not status == 0:
    sys.exit('something went wrong with refinem scaffold_stats, exit')


filter_dir = genomic_dir+'/'+'filter'
if os.path.exists(filter_dir) :
    sys.exit(filter_dir+' already exist, please remove it first')
os.mkdir(filter_dir)

cmd = 'source activate refineM-0.1.2 && refinem filter_bins '+bin_dir+' '+outliers_dir+'/outliers.tsv '+filter_dir
print(cmd)
status = os.system(cmd)
print('status: '+str(status))
if not status == 0:
    sys.exit('something went wrong with refinem filter_bins, exit')
print('\n\n')


####################
# refineM taxonomy #
####################

gene_dir = anvio_directory+'/'+'genes'
if os.path.exists(gene_dir) :
    sys.exit(gene_dir_dir+' already exist, please remove it first')
os.mkdir(gene_dir)

cmd = 'source activate refineM-0.1.2 && refinem call_genes -c '+cpu+' '+bin_dir+' '+gene_dir
print(cmd)
status = os.system(cmd)
print('status: '+str(status))
if not status == 0:
    sys.exit('something went wrong with refinem call_genes, exit')

reference_taxonomy_filename = '/env/cns/proj/agc/scratch/proj/GTDB/gtdb_r95_taxonomy.2020-07-30.tsv'
reference_db_filename = '/env/cns/proj/agc/scratch/proj/GTDB/gtdb_r95_protein_db.2020-07-30.faa.dmnd'

taxo_dir = refineM_dir+'/'+'taxonomy'
if os.path.exists(taxo_dir) :
    sys.exit(taxo_dir+' already exist, please remove it first')
os.mkdir(taxo_dir)

taxoProfile_dir = taxo_dir+'/'+'profiles'
if os.path.exists(taxoProfile_dir) :
    sys.exit(taxoProfile_dir+' already exist, please remove it first')
os.mkdir(taxoProfile_dir)


cmd = 'source activate refineM-0.1.2 && refinem taxon_profile -c '+cpu+' '+gene_dir+' '+stat_dir+'/scaffold_stats.tsv'+' '+reference_db_filename+' '+reference_taxonomy_filename+' '+taxoProfile_dir
print(cmd)
status = os.system(cmd)
print('status: '+str(status))
if not status == 0:
    sys.exit('something went wrong with refinem taxon_profile, exit')



taxoOutlier_dir = taxo_dir+'/'+'outliers'
if os.path.exists(taxoOutlier_dir) :
    sys.exit(taxoOutlier_dir+' already exist, please remove it first')
os.mkdir(taxoOutlier_dir)

taxonFilter_filename = taxoOutlier_dir+'/'+'taxon_filter.tsv'
cmd = 'source activate refineM-0.1.2 && refinem taxon_filter -c '+cpu+' '+taxoProfile_dir+' '+taxonFilter_filename
print(cmd)
status = os.system(cmd)
print('status: '+str(status))
if not status == 0:
    sys.exit('something went wrong with refinem taxon_filter, exit')



taxoFilter_dir = taxo_dir+'/'+'filters'
if os.path.exists(taxoFilter_dir) :
    sys.exit(taxoFilter_dir+' already exist, please remove it first')
os.mkdir(taxoFilter_dir)

cmd = 'source activate refineM-0.1.2 && refinem filter_bins '+bin_dir+' '+taxonFilter_filename+' '+taxoFilter_dir
print(cmd)
status = os.system(cmd)
print('status: '+str(status))
if not status == 0:
    sys.exit('something went wrong with refinem filter_bins, exit')




#######################
# parsing the results #
#######################

