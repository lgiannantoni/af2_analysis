#!/usr/bin/env python3
# coding: utf-8

import os
import numpy as np
import pandas as pd
import json
import pdb_numpy
import seaborn as sns
import matplotlib.pyplot as plt
from cmcrameri import cm
from tqdm.auto import tqdm

from .format import colabfold_1_5, default
from . import sequence, plot

class Data:
    """ Data class

    Parameters
    ----------
    dir : str
        Path to the directory containing the `log.txt` file.
    format : str
        Format of the data.
    df : pandas.DataFrame
        Dataframe containing the information extracted from the `log.txt` file.
    """
    
    def __init__(self, directory=None):
        """
        """

        if directory is not None:
            self.read_directory(directory)
    
    def read_directory(self, directory, keep_recycles=False):
        """ Read a directory.

        If the directory contains a `log.txt` file, the format is set to `colabfold_1.5`.

        Parameters
        ----------
        directory : str
            Path to the directory containing the `log.txt` file.
        
        Returns
        -------
        None
        """
        self.dir = directory

        if os.path.isfile(os.path.join(directory, 'log.txt')):
            self.format = 'colabfold_1.5'
            self.df = colabfold_1_5.read_log(directory, keep_recycles)
            self.add_pdb()
            self.add_json()
        else:
            self.format = 'default'
            self.df = default.read_dir(directory)
            self.add_json()
            self.extract_json()

        # Read the first pdb to extract chain lengths:
        first_model = pdb_numpy.Coor(self.df.loc[0, 'pdb'])
        self.chains = list(np.unique(first_model.models[0].chain))
        self.chain_length = [len(np.unique(first_model.models[0].uniq_resid[first_model.models[0].chain == chain] )) for chain in self.chains]


    def add_json(self):
        """ Add json files to the dataframe.
        
        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if self.format == 'colabfold_1.5':
            colabfold_1_5.add_json(self.df, self.dir)
        if self.format == 'default':
            default.add_json(self.df, self.dir)
    
    def extract_json(self):
        """ Extract json files to the dataframe.
        
        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        index_list = []
        json_list = []

        for i, row in self.df.iterrows():
            if row.json is not None:
                index_list.append(i)
                
                with open(row.json, 'r') as f:
                    data = json.load(f)
                
                json_list.append(data)
        
        new_column = {}
        for keys in json_list[0].keys():
            new_column[keys] = []
        for data in json_list:
            for keys in data.keys():
                new_column[keys].append(data[keys])
        
        for keys in new_column.keys():
            self.df[keys] = np.nan
            new_col = pd.Series(new_column[keys], index=index_list)
            self.df[keys].iloc[index_list] = new_col

    def add_pdb(self):
        """ Add pdb files to the dataframe.
        
        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if self.format == 'colabfold_1.5':
            colabfold_1_5.add_pdb(self.df, self.dir)

    def add_fasta(self, csv):
        """ Add fasta sequence to the dataframe.
        
        Parameters
        ----------
        csv : str
            Path to the csv file containing the fasta sequence.

        Returns
        -------
        None
        """
            
        if self.format == 'colabfold_1.5':
            colabfold_1_5.add_fasta(self.df, csv)
    
    def keep_last_recycle(self):
        """ Keep only the last recycle for each query.

        """

        idx = self.df.groupby(['query', 'seed', 'model', 'weight'])['recycle'].transform(max) == self.df['recycle']
        self.df = self.df[idx]


    def plot_maxscore_as_col(self, score, col, hue='query'):
        
        col_list = self.df[col].unique()
        query_list = self.df[hue].unique()
        #print(col_list)
        #print(query_list)
        
        out_list = []
        
        for query in query_list:
            #print(query)
            query_pd = self.df[ self.df[hue] == query]
            
            for column in col_list:
                #print(column)
                #~print()
                
                col_pd = query_pd [ query_pd[col] <= column ]
                #print(col_pd[score])
                #print(column, len(col_pd))
                #print(col, col_pd.columns)
                
                if len(col_pd) > 0:
                
                    out_list.append({
                        hue: query,
                        score: col_pd[score].max(),
                        col: column})
                    #print(column, len(col_pd), col_pd[score].max())
        
        max_pd = pd.DataFrame(out_list)
    
        fig, ax = plt.subplots()
        sns.lineplot(max_pd, x=col, y=score, hue=hue)

        return(fig, ax)
    
    def plot_pae(self, index, cmap=cm.vik):

        row = self.df.iloc[index]

        if row['json'] is None:
            return(None, None)

        with open(row['json']) as f:
            local_json = json.load(f)
        
        pae_array = np.array(local_json['pae'])

        fig, ax = plt.subplots()
        res_max = sum(self.chain_length)
        img = ax.imshow(
            pae_array, cmap=cmap,
            vmin=0., vmax=30.,
            )#+extent=[0, res_max, 0, res_max])
        plt.hlines(np.cumsum(self.chain_length[:-1]), xmin=0, xmax=res_max, colors='black')
        plt.vlines(np.cumsum(self.chain_length[:-1]), ymin=0, ymax=res_max, colors='black')
        plt.xlim(0,res_max)
        plt.ylim(res_max,0)
        ax.set_yticklabels(self.chains)
        chain_pos = []
        len_sum = 0
        for longueur in self.chain_length:
            chain_pos.append(len_sum+longueur/2)
            len_sum += longueur

        ax.set_yticks(chain_pos)
        cbar = plt.colorbar(img)
        cbar.set_label('Predicted Aligned Error (Å)', rotation=270)
        cbar.ax.get_yaxis().labelpad = 15


        return(fig, ax)

    def plot_plddt(self, index_list):


        fig, ax = plt.subplots()

        for index in index_list:

            row = self.df.iloc[index]

            if row['json'] is None:
                return(None, None)

            with open(row['json']) as f:
                local_json = json.load(f)
            
            plddt_array = np.array(local_json['plddt'])

            plt.plot(plddt_array)

        plt.vlines(np.cumsum(self.chain_length[:-1]), ymin=0, ymax=100.0, colors='black')
        plt.ylim(0,100)
        plt.xlim(0,sum(self.chain_length))
        plt.xlabel('Residue')
        plt.ylabel('predicted LDDT')

        return(fig, ax)

    def show_3d(self, index):

        row = self.df.iloc[index]

        if row['pdb'] is None:
            return(None, None)

        import nglview as nv

        # Bug with show_file
        # view = nv.show_file(row['pdb'])
        view = nv.show_structure_file(row['pdb'])
        #view.add_component(ref_coor[0])
        #view.clear_representations(1)
        #view[1].add_cartoon(selection="protein", color='blue')
        #view[1].add_licorice(selection=":A", color='blue')
        #view[0].add_licorice(selection=":A")
        return view
    
    def compute_pdockq(self):
        """
        Compute pdockq from the pdb file.
        
        """

        from pdb_numpy.analysis import compute_pdockQ

        pdockq_list = []

        for pdb in tqdm(self.df['pdb'], total=len(self.df['pdb'])):
            if pdb:
                model = pdb_numpy.Coor(pdb)
                pdockq_list += compute_pdockQ(model)
            else:
                pdockq_list.append(None)

        self.df['pdockq'] = pdockq_list

    def compute_pdockq2(self):
        """
        Compute pdockq2 from the pdb file.

        $$ pDockQ_2 = \frac{L}{1 + exp [-k*(X_i-X_0)]} + b$$

        with

        $$ X_i = \langle \frac{1}{1+(\frac{PAE_{int}}{d_0})^2} \rangle - \langle pLDDT \rangle_{int}$$

        Ref:
        https://academic.oup.com/bioinformatics/article/39/7/btad424/7219714
        """
        cutoff = 8.0
        L ,x0, k, b = 1.31034849e+00, 8.47326239e+01, 7.47157696e-02, 5.01886443e-03
        d0 = 10.0
        pdockq_list = []
        for chain in self.chains:
            pdockq_list.append([])

        for pdb, json_path in tqdm(zip(self.df['pdb'], self.df['json']), total=len(self.df['pdb'])):
            if pdb and json_path:
                model = pdb_numpy.Coor(pdb)
                model_CA = model.select_atoms('name CA')
                for i, chain in enumerate(self.chains):
                    # print(i, chain)
                    interface_sel = model_CA.select_atoms(f"(chain {chain} and within {cutoff} of not chain {chain}) or (not chain {chain} and within {cutoff} of chain {chain})")                    
                    plddt_avg = np.mean(interface_sel.beta)

                    chain_sel = model_CA.select_atoms(f"(chain {chain} and within {cutoff} of not chain {chain})")
                    inter_chain_sel = model_CA.select_atoms(f"(not chain {chain} {chain} and within {cutoff} of chain {chain})")

                    with open(json_path) as f:
                        local_json = json.load(f)
                    pae_array = np.array(local_json['pae'])


                    # print(chain_sel.uniq_resid, inter_chain_sel.uniq_resid)
                    # print(f"pLDDT = {plddt_avg}")
                    # print(len(chain_sel.uniq_resid), len(inter_chain_sel.uniq_resid))
                    #if len(chain_sel.uniq_resid) + len(inter_chain_sel.uniq_resid) == 0:
                    #    print(f"chain {chain} pdockq2 = None")
                    #    pdockq_list[i].append(None)
                    #    continue
                    # print(chain_sel.uniq_resid, inter_chain_sel.uniq_resid)
                    # print(pae_array)
                    # print(pae_array.shape)
                    # print(pae_array[chain_sel.uniq_resid][:, inter_chain_sel.uniq_resid])
                    # print(pae_array[chain_sel.uniq_resid][:, inter_chain_sel.uniq_resid].shape)
                    norm_if_interpae = np.mean(1/(1+(pae_array[chain_sel.uniq_resid][:, inter_chain_sel.uniq_resid]/d0)**2))
                    norm_if_interpae_sym = np.mean(1/(1+(pae_array[inter_chain_sel.uniq_resid][:,chain_sel.uniq_resid]/d0)**2))
                    # print(f"norm_if_interpae = {norm_if_interpae:.3f}, symetry: {norm_if_interpae_sym:.3f}")
                    x = norm_if_interpae * plddt_avg
                    y = L / (1 + np.exp(-k*(x-x0)))+b
                    # print(f"chain {chain} pdockq2 = {y}")
                    pdockq_list[i].append(y)
                    
            else:
                for list in pdockq_list:
                    list.append(None)

        # print(pdockq_list)
        for i, chain in enumerate(self.chains):
            self.df[f'pdockq2_{chain}'] = pdockq_list[i]

    def plot_msa(self):
        """
        Plot the msa from the a3m file.
        
        ..Warning only tested with colabfold 1.5
        """

        raw_list = os.listdir(self.dir)
        file_list = []
        for file in raw_list:
            if file.endswith(".a3m"):
                file_list.append(file)
        
        for a3m_file in file_list:
            print(a3m_file)

            a3m_lines = open(os.path.join(self.dir, a3m_file),"r").readlines()[1:]
            seqs, mtx, nams = sequence.parse_a3m(a3m_lines=a3m_lines)
            feature_dict = {}
            feature_dict["msa"] = sequence.convert_aa_msa(seqs)
            feature_dict['num_alignments'] = len(seqs)
            feature_dict["asym_id"] = []
            for i, chain_len in enumerate(self.chain_length):
                feature_dict["asym_id"] += [i+1]*chain_len
            fig = plot.plot_msa_v2(feature_dict)

