# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from geopy import distance
# import descartes
import geopandas as gpd
from shapely.geometry import Point, Polygon
from matplotlib.colors import TwoSlopeNorm

###User defined variables###
RTS = [68] #Number of nodes to retain (can be a single number or series of numbers to create different topologies automatically)
MRE = 10 # Number of MRE nodes
distance_threshold = 30 #Distance threshold in km, restricts algorithm to select any two nodes that are closer than this number (this is used when selecting a single node in each BA)
distance_threshold2 = 80 #Distance threshold in km, restricts algorithm to select any two nodes that are closer than this number (this is used after we selected a single node in each BA)
############################

df_BAs = pd.read_csv('../Data_setup/Time_series_data/BA_data/BAs.csv',header=0)
BAs = list(df_BAs['Name'])

df = pd.read_csv('../Data_setup/10k_topology_files/10k_load.csv',header=0)
crs = {'init':'epsg:4326'}
# crs = {"init": "epsg:2163"}
geometry = [Point(xy) for xy in zip(df['Substation Longitude'],df['Substation Latitude'])]
filter_nodes = gpd.GeoDataFrame(df,crs=crs,geometry=geometry)
nodes_df = gpd.GeoDataFrame(df,crs=crs,geometry=geometry)
nodes_df = nodes_df.to_crs(epsg=2163)

BAs_gdf = gpd.read_file('../Data_setup/Shapefiles/WECC.shp')
BAs_gdf = BAs_gdf.to_crs(epsg=2163)

states_gdf = gpd.read_file('../Data_setup/Shapefiles/geo_export_9ef76f60-e019-451c-be6b-5a879a5e7c07.shp')
states_gdf = states_gdf.to_crs(epsg=2163)

joined = gpd.sjoin(nodes_df,BAs_gdf,how='left',op='within')
joined2 = gpd.sjoin(nodes_df,states_gdf,how='left',op='within')
joined['State'] = joined2['state_name']

buses = list(joined['Number'])
B = []
for b in buses:
    if b in B:
        pass
    else:
        B.append(b)
        
#elimate redundant buses (overlapping BAs) based on peak load and 
#location within BAs

selected_BAs = []

for b in B:
    
    sample = joined[joined['Number'] == b]
    sample = sample.reset_index(drop=True)
    
    TELL_ok = []
    
    if len(sample) > 1:
        
        for i in range(0,len(sample)):
            if sample.loc[i,'NAME'] in BAs:
                TELL_ok.append(i)
        
        if len(TELL_ok)<1:
            
            smallest = min(sample['SHAPE_Area'])
            selection = sample[sample['SHAPE_Area']==smallest]
            
        else:
            
            t = 0
            m = 100000000000000000000
            for i in range(0,len(TELL_ok)):
                if sample.loc[TELL_ok[i],'NAME'] in selected_BAs:
                    if sample.loc[TELL_ok[i],'SHAPE_Area'] < m:
                        m = sample.loc[TELL_ok[i],'SHAPE_Area']
                else:
                    t = 1
                    selection = sample.loc[TELL_ok[i],:]
                    selected_BAs.append(sample.loc[TELL_ok[i],'NAME'])
                    break 
            if t < 1:
                selection = sample.loc[sample['SHAPE_Area']==m]
            
    else:
        
        selection = sample
        
        if sample['NAME'][0] in selected_BAs:
            pass
        else:
            selected_BAs.append(sample['NAME'][0])
        
    b_idx = B.index(b)
    print(b_idx)
    
    if b_idx < 1:
        
        combined = selection
    
    else:
        
        combined = combined.append(selection) 

###########################################
# Remove any entry that is not in a TELL BA
combined = combined.reset_index(drop=True)

for i in range(0,len(combined)):
    a = combined.loc[i,'NAME']
    if a in BAs:
        pass
    else:
        combined = combined.drop([i])

combined = combined.reset_index(drop=True)    
combined.to_csv('../Data_setup/10k_topology_files/nodes_to_BA_state.csv')

##############################
#  Generators
##############################

import re
from itertools import compress

df_BA_states = pd.read_csv('../Data_setup/10k_topology_files/nodes_to_BA_state.csv',index_col=0)
df_gens = pd.read_csv('../Data_setup/10k_topology_files/10k_Gen.csv')

###########################################
# Remove any entry that is not in a TELL BA
nodes = list(df_BA_states['Number'])

for i in range(0,len(df_gens)):
    a = df_gens.loc[i,'BusNum']
    if a in nodes:
        pass
    else:
        df_gens = df_gens.drop([i])
df_gens = df_gens.reset_index(drop=True)

names = list(df_gens['BusName'])
BAs = []
c = list(df_BA_states.columns)
nx = int(c.index('NAME'))

# remove numbers and spaces
for n in names:
    i = names.index(n)
    corrected = re.sub(r'[^A-Z]',r'',n)
    names[i] = corrected
    BA = df_BA_states[df_BA_states['Number'] == df_gens.loc[i,'BusNum']]
    BAs.append(BA.iloc[0,nx])
    
df_gens['BusName'] = names
df_gens['BA'] = BAs
types = list(df_gens['FuelType'])

#select a single bus for each plant/BA combination (generators with the same name)

leftover = []
reduced_gen_buses = []
unique_bus_names = []
unique_bus_types = []
caps = []

for n in names:
    idx = names.index(n)
    if n in unique_bus_names:
        pass
    else:
        unique_bus_names.append(n)
        unique_bus_types.append(types[idx])
        
df_T = pd.DataFrame(unique_bus_types)
df_T.columns = ['Type']
# df_T.to_csv('reduced_types.csv')

for n in unique_bus_names:
    sample_ba = list(df_gens.loc[df_gens['BusName'] == n,'BA'].values)
    sample_bus_number = list(df_gens.loc[df_gens['BusName'] == n,'BusNum'].values)
    sample_bus_cap = list(df_gens.loc[df_gens['BusName'] == n,'MWMax'].values)
    
    s = []
    s_n = []
    s_c = []
    
    # record each BA for this plant
    for i in sample_ba:
        if i in s:
            pass
        else:
            s.append(i)
            
            #find max cap generator at this plant/BA combination
            idx = [ True if x == i else False for x in sample_ba]
            s_bn = list(compress(sample_bus_number,idx))
            s_cp = list(compress(sample_bus_cap,idx))
            mx = np.max(s_cp)
            total = np.sum(s_cp)
            idx2 = s_cp.index(mx)
            s_n.append(s_bn[idx2])
            s_c.append(total)
            
    if len(s)>1:
        if n in leftover:
            pass
        else:
            leftover.append(n)
        for j in range(0,len(s)):
            reduced_gen_buses.append(s_n[j])
            caps.append(s_c[j])
    else:
        reduced_gen_buses.append(s_n[0])
        caps.append(s_c[0])

##################################
#LOAD
##################################

df_load = pd.read_csv('../Data_setup/10k_topology_files/10k_Load.csv')

for i in range(0,len(df_load)):
    a = df_load.loc[i,'Number']
    if a in nodes:
        pass
    else:
        df_load = df_load.drop([i])
df_load = df_load.reset_index(drop=True)

#pull all nodes with >0 load
non_zero = list(df_load.loc[df_load['Load MW']>0,'Number'])
unique_non_zero = []
for i in non_zero:
    if i in reduced_gen_buses:
        pass
    else:
        unique_non_zero.append(i)

#pull all nodes with voltage > 500kV
major_V = list(df_load.loc[df_load['Nom kV']>500,'Number'])
unique_major_V = []
for i in major_V:
    if i in reduced_gen_buses:
        pass
    elif i in unique_non_zero:
        pass
    else:
        unique_major_V.append(i)
        
#Calculate load weights for State/BA combinations
states = list(df_BA_states['State'].unique())
states = [x for x in states if str(x) != 'nan']
BAs = list(df_BA_states['NAME'].unique())
BAs = [x for x in BAs if str(x) != 'nan']

keys=[]
loads=[]
max_loads = []

for i in non_zero:
    
    area = df_BA_states.loc[df_BA_states['Number']==i,'NAME'].values[0]
    state = df_BA_states.loc[df_BA_states['Number']==i,'State'].values[0]
    
    if str(area) == 'nan' or str(state) == 'nan':
        pass
    else:
    
        l = df_load.loc[df_load['Number']==i,'Load MW'].values
        
        t = tuple([str(area),str(state)])
        
        if t in keys:
            idx=keys.index(t)
            loads[idx] += l    
            if max_loads[idx] < l:
                max_loads[idx] = i
        else:
            keys.append(t)
            loads.append(l)
            max_loads.append(i)

load_weights = loads/sum(loads)

#Create analogous generation weights

gens = []
gen_keys = []

for i in reduced_gen_buses:
    
    x = reduced_gen_buses.index(i)
    
    area = df_BA_states.loc[df_BA_states['Number']==i,'NAME'].values[0]
    state = df_BA_states.loc[df_BA_states['Number']==i,'State'].values[0]
    
    if str(area) == 'nan' or str(state) == 'nan':
        pass
    else:
    
        t = tuple([str(area),str(state)])
        
        if t in gen_keys:
            idx=gen_keys.index(t)
            gens[idx] += caps[x]
            
        else:
            gen_keys.append(t)
            gens.append(caps[x])
        
gen_weights = gens/sum(gens)

##############################
#Nodal reduction
##############################

#Updating load dataframe
df_load_upt = df_load.copy()
df_load_upt.dropna(subset=['Load MW'], inplace=True)
df_load_upt.index = df_load_upt['Number']

#Listing all states
coast_states = ['Washington','Oregon','California']
inland_states = ['Idaho','Nevada','Arizona','Utah','New Mexico','Wyoming','Texas','Colorado','Montana']

# #Finding total demand at each state
# total_demand = []
# for i in inland_states:
    
#     state_nodes = list(df_BA_states.loc[df_BA_states['State']==i,'Number'])
#     sum_demand = df_load_upt.loc[df_load_upt['Number'].isin(state_nodes)]['Load MW'].sum()
#     total_demand.append(sum_demand)

# state_demands = pd.DataFrame(list(zip(inland_states,total_demand)),columns=['State','Demand_MW'])
# state_demands_sort = state_demands.sort_values(by='Demand_MW',ascending=False).reset_index(drop=True)

for NN in RTS:
    
    #Adding selected MRE nodes
    MRE_selected_nodes = [10006,10003,13026,13022,13012,13003,20007,20003,20012,21004]
    
    #1 - Selecting highest demand nodes in each BA
    inland_state_nodes = []
    my_BAS = []
    #Finding highest load node in each BA
    for BA_sp in BAs:
        
        updated_df_BA = df_BA_states[~df_BA_states['Number'].isin(MRE_selected_nodes)]
        BA_demand_nodes = list(updated_df_BA.loc[updated_df_BA['NAME']==BA_sp,'Number'])
        demand_nodes_sorted = df_load_upt.loc[df_load_upt['Number'].isin(BA_demand_nodes)].sort_values(by='Load MW',ascending=False)

        for i in range(len(demand_nodes_sorted)):

            highest_demand_node = demand_nodes_sorted['Load MW'].index[i]
            my_state = df_BA_states.loc[df_BA_states['Number']==highest_demand_node]['State'].values[0]
            my_distances = []
            
            if len(inland_state_nodes) == 0:
                inland_state_nodes.append(highest_demand_node)
                my_BAS.append(BA_sp)
                break
            
            elif highest_demand_node in inland_state_nodes:
                continue
            
            else:
                
                if BA_sp == 'WESTERN AREA POWER ADMINISTRATION - ROCKY MOUNTAIN REGION':
                    
                    if my_state == 'Wyoming':
                        
                        LA = filter_nodes.loc[filter_nodes['Number']==highest_demand_node,'Substation Latitude'].values[0]
                        LO = filter_nodes.loc[filter_nodes['Number']==highest_demand_node,'Substation Longitude'].values[0]
                        T1 = tuple((LA,LO))
                        
                        for z in inland_state_nodes:
                            
                            a = filter_nodes.loc[filter_nodes['Number']==z,'Substation Latitude'].values[0]
                            b = filter_nodes.loc[filter_nodes['Number']==z,'Substation Longitude'].values[0]
                            T2 = tuple((a,b))
                            
                            my_dist = distance.distance(T1,T2).km
                            my_distances.append(my_dist)
                    
                        if any(x < distance_threshold for x in my_distances):
                            continue
                        else:
                            inland_state_nodes.append(highest_demand_node)
                            my_BAS.append(BA_sp)
                            break
                    
                    else:
                        continue 
                    
                elif BA_sp == 'PUBLIC SERVICE COMPANY OF NEW MEXICO':
                    
                    if my_state == 'New Mexico':
                        
                        LA = filter_nodes.loc[filter_nodes['Number']==highest_demand_node,'Substation Latitude'].values[0]
                        LO = filter_nodes.loc[filter_nodes['Number']==highest_demand_node,'Substation Longitude'].values[0]
                        T1 = tuple((LA,LO))
                        
                        for z in inland_state_nodes:
                            
                            a = filter_nodes.loc[filter_nodes['Number']==z,'Substation Latitude'].values[0]
                            b = filter_nodes.loc[filter_nodes['Number']==z,'Substation Longitude'].values[0]
                            T2 = tuple((a,b))
                            
                            my_dist = distance.distance(T1,T2).km
                            my_distances.append(my_dist)
                    
                        if any(x < distance_threshold for x in my_distances):
                            continue
                        else:
                            inland_state_nodes.append(highest_demand_node)
                            my_BAS.append(BA_sp)
                            break
                        
                    else:
                        continue 
        
                else: 
                
                    LA = filter_nodes.loc[filter_nodes['Number']==highest_demand_node,'Substation Latitude'].values[0]
                    LO = filter_nodes.loc[filter_nodes['Number']==highest_demand_node,'Substation Longitude'].values[0]
                    T1 = tuple((LA,LO))
                    
                    for z in inland_state_nodes:
                        
                        a = filter_nodes.loc[filter_nodes['Number']==z,'Substation Latitude'].values[0]
                        b = filter_nodes.loc[filter_nodes['Number']==z,'Substation Longitude'].values[0]
                        T2 = tuple((a,b))
                        
                        my_dist = distance.distance(T1,T2).km
                        my_distances.append(my_dist)
                
                    if any(x < distance_threshold for x in my_distances):
                        continue
                    else:
                        inland_state_nodes.append(highest_demand_node)
                        my_BAS.append(BA_sp)
                        break
    
    nodes_to_avoid = MRE_selected_nodes + inland_state_nodes
    
    #Finding how many nodes are going to be selected for coastal states
    remaining_nodes = NN - len(inland_state_nodes) - MRE
    g_N = int(np.floor(remaining_nodes*.33)) #generation nodes
    l_N = int(np.floor(remaining_nodes*.33)) #demand nodes
    t_N = int(np.floor(remaining_nodes*.33)) #transmission nodes
    to_be_allocated_nodes = g_N + l_N + t_N
    if to_be_allocated_nodes < remaining_nodes:
        l_N += remaining_nodes - to_be_allocated_nodes
    else:
        pass
    
    #2 - allocate remaining demand nodes based on MW ranking of individual nodes in coastal states
    unallocated = [i for i in non_zero if i not in nodes_to_avoid]
    load_ranks = np.zeros((len(unallocated),2))
    
    for i in unallocated:
        idx = unallocated.index(i)
        load_ranks[idx,0] = i
        load_ranks[idx,1] = df_load.loc[df_load['Number']==i,'Load MW'].values
    df_load_ranks = pd.DataFrame(load_ranks)
    df_load_ranks.columns = ['BusName','MW']
    df_load_ranks = df_load_ranks.sort_values(by='MW',ascending=False)
    df_load_ranks = df_load_ranks.reset_index(drop=True)
    
    added = 0
    while l_N > 0:
      
        p = int(df_load_ranks.loc[added,'BusName'])
        
        my_state = df_BA_states.loc[df_BA_states['Number']==p]['State'].values[0]
        
        if my_state in coast_states:
        
            LA = filter_nodes.loc[filter_nodes['Number']==p,'Substation Latitude'].values[0]
            LO = filter_nodes.loc[filter_nodes['Number']==p,'Substation Longitude'].values[0]
            T1 = tuple((LA,LO))
            
            trigger = 0
            
            for d in inland_state_nodes:
                a = filter_nodes.loc[filter_nodes['Number']==d,'Substation Latitude'].values[0]
                b = filter_nodes.loc[filter_nodes['Number']==d,'Substation Longitude'].values[0]
                T2 = tuple((a,b))
                
                dist = distance.distance(T1,T2).km
                
                if dist < distance_threshold2:
                    
                    trigger = 1
            
            if trigger > 0:
                added += 1
            else:
                
                inland_state_nodes.append(int(df_load_ranks.loc[added,'BusName']))
                added += 1  
                l_N += -1
                
        else:
            added += 1
            
    
    #3 - allocate generation based on reduced gens (screen for overlap)
    
    gen_nodes_selected = []
    unallocated_gens = [i for i in reduced_gen_buses if i not in nodes_to_avoid]
    unallocated_caps = []
    for i in unallocated_gens:
        idx = reduced_gen_buses.index(i)
        unallocated_caps.append(caps[idx])
    
    df_gen_ranks = pd.DataFrame()
    df_gen_ranks['BusName'] = unallocated_gens
    df_gen_ranks['MW'] = unallocated_caps
    
    df_gen_ranks = df_gen_ranks.sort_values(by='MW',ascending=False)
    df_gen_ranks = df_gen_ranks.reset_index(drop=True)
    
    added = 0
    while g_N > 0:
           
        p = int(df_gen_ranks.loc[added,'BusName'])
        
        my_state = df_BA_states.loc[df_BA_states['Number']==p]['State'].values[0]
        
        if my_state in coast_states:
        
            LA = filter_nodes.loc[filter_nodes['Number']==p,'Substation Latitude'].values[0]
            LO = filter_nodes.loc[filter_nodes['Number']==p,'Substation Longitude'].values[0]
            T1 = tuple((LA,LO))
            
            trigger = 0
            
            N = gen_nodes_selected + inland_state_nodes
            
            for d in N:
                a = filter_nodes.loc[filter_nodes['Number']==d,'Substation Latitude'].values[0]
                b = filter_nodes.loc[filter_nodes['Number']==d,'Substation Longitude'].values[0]
                T2 = tuple((a,b))
                
                dist = distance.distance(T1,T2).km
                
                if dist < distance_threshold2:
                    
                    trigger = 1
            
            if trigger > 0:
                added += 1
            else:
                
                gen_nodes_selected.append(int(df_gen_ranks.loc[added,'BusName']))
                added += 1  
                g_N += -1
                
        else:
            added += 1
        
        
    
    #4 - allocate transmission nodes based on load as well (screen for overlap, make sure list is for >=345kV)
    trans_nodes_selected = []
    unallocated_trans = [i for i in non_zero if i not in nodes_to_avoid]
    unallocated_trans = [i for i in unallocated_trans if i not in gen_nodes_selected]
    
    load_ranks = np.zeros((len(unallocated_trans),2))
    
    for i in unallocated_trans:
        idx = unallocated_trans.index(i)
        load_ranks[idx,0] = i
        load_ranks[idx,1] = df_load.loc[df_load['Number']==i,'Load MW'].values
    df_load_ranks = pd.DataFrame(load_ranks)
    df_load_ranks.columns = ['BusName','MW']
    df_load_ranks = df_load_ranks.sort_values(by='MW',ascending=False)
    df_load_ranks = df_load_ranks.reset_index(drop=True)
    
    added = 0
    while t_N > 0:
    
        p = int(df_load_ranks.loc[added,'BusName'])
        
        my_state = df_BA_states.loc[df_BA_states['Number']==p]['State'].values[0]
        
        if my_state in coast_states:
        
            LA = filter_nodes.loc[filter_nodes['Number']==p,'Substation Latitude'].values[0]
            LO = filter_nodes.loc[filter_nodes['Number']==p,'Substation Longitude'].values[0]
            T1 = tuple((LA,LO))
            
            trigger = 0
            
            N = gen_nodes_selected + inland_state_nodes + trans_nodes_selected
            
            for d in N:
                a = filter_nodes.loc[filter_nodes['Number']==d,'Substation Latitude'].values[0]
                b = filter_nodes.loc[filter_nodes['Number']==d,'Substation Longitude'].values[0]
                T2 = tuple((a,b))
                
                dist = distance.distance(T1,T2).km
                
                if dist < distance_threshold2:
                    
                    trigger = 1
            
            if trigger > 0:
                added += 1
            else:
                
                trans_nodes_selected.append(int(df_load_ranks.loc[added,'BusName']))
                added += 1  
                t_N += -1
                
        else:
            added += 1
    
    
        
    # # plot (unique colors, and combos)
    
    fig,ax = plt.subplots()
    states_gdf.plot(ax=ax,color='white',edgecolor='black',linewidth=0.5)
    # nodes_df.plot(ax=ax,color = 'lightgray',alpha=1)
    M=18
    
    G_NODES = nodes_df[nodes_df['Number'].isin(gen_nodes_selected)]
    G_NODES.plot(ax=ax,color = 'deepskyblue',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='Generator Nodes')
    
    D_NODES = nodes_df[nodes_df['Number'].isin(inland_state_nodes)]
    D_NODES.plot(ax=ax,color = 'deeppink',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='Demand Nodes')
    
    T_NODES = nodes_df[nodes_df['Number'].isin(trans_nodes_selected)]
    T_NODES.plot(ax=ax,color = 'limegreen',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='Transmission Nodes') 
    
    MRE_NODES = nodes_df[nodes_df['Number'].isin(MRE_selected_nodes)]
    MRE_NODES.plot(ax=ax,color = 'darkviolet',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='MRE Nodes')
    
    ax.set_box_aspect(1)
    ax.set_xlim(-2000000,0)
    ax.set_ylim([-1750000,750000])
    plt.axis('off')
    fig.legend(loc='center', bbox_to_anchor=(0.5, -0.12), ncol=2, bbox_transform=ax.transAxes, fontsize=7)
    plt.savefig('draft_topology.jpg',dpi=330, bbox_inches='tight')
    
    
    #SO-CAL
    fig,ax = plt.subplots()
    states_gdf.plot(ax=ax,color='white',edgecolor='black',linewidth=0.5)
    # nodes_df.plot(ax=ax,color = 'lightgray',alpha=1)
    M=18
    
    G_NODES.plot(ax=ax,color = 'deepskyblue',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='Generator Nodes')
    D_NODES.plot(ax=ax,color = 'deeppink',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='Demand Nodes')
    T_NODES.plot(ax=ax,color = 'limegreen',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='Transmission Nodes')   
    MRE_NODES.plot(ax=ax,color = 'darkviolet',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='MRE Nodes')
    
    ax.set_box_aspect(1)
    ax.set_xlim(-1800000,-1100000)
    ax.set_ylim([-1400000,-700000])
    plt.axis('off')
    fig.legend(loc='center', bbox_to_anchor=(0.5, -0.12), ncol=2, bbox_transform=ax.transAxes, fontsize=7)
    plt.savefig('SOCAL_topology.jpg',dpi=330, bbox_inches='tight')
    
    
    #Mid-C
    fig,ax = plt.subplots()
    states_gdf.plot(ax=ax,color='white',edgecolor='black',linewidth=0.5)
    # nodes_df.plot(ax=ax,color = 'lightgray',alpha=1)
    M=18
    
    G_NODES.plot(ax=ax,color = 'deepskyblue',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='Generator Nodes')
    D_NODES.plot(ax=ax,color = 'deeppink',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='Demand Nodes')
    T_NODES.plot(ax=ax,color = 'limegreen',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='Transmission Nodes')   
    MRE_NODES.plot(ax=ax,color = 'darkviolet',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='MRE Nodes')
    
    ax.set_box_aspect(1)
    ax.set_xlim(-2000000,-1000000)
    ax.set_ylim([0,750000])
    plt.axis('off')
    fig.legend(loc='center', bbox_to_anchor=(0.5, -0.12), ncol=2, bbox_transform=ax.transAxes, fontsize=7)
    plt.savefig('MIDC_topology.jpg',dpi=330, bbox_inches='tight')
    
    
    #SF Bay Area
    fig,ax = plt.subplots()
    states_gdf.plot(ax=ax,color='white',edgecolor='black',linewidth=0.5)
    # nodes_df.plot(ax=ax,color = 'lightgray',alpha=1)
    M=18
    
    G_NODES.plot(ax=ax,color = 'deepskyblue',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='Generator Nodes')
    D_NODES.plot(ax=ax,color = 'deeppink',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='Demand Nodes')
    T_NODES.plot(ax=ax,color = 'limegreen',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='Transmission Nodes')   
    MRE_NODES.plot(ax=ax,color = 'darkviolet',markersize=M,alpha=1,edgecolor='black',linewidth=0.3, label='MRE Nodes')
    
    ax.set_box_aspect(1)
    ax.set_xlim(-2000000,-1500000)
    ax.set_ylim([-750000,0])
    plt.axis('off')
    fig.legend(loc='center', bbox_to_anchor=(0.5, -0.12), ncol=2, bbox_transform=ax.transAxes, fontsize=7)
    plt.savefig('SF_topology.jpg',dpi=330, bbox_inches='tight')
    
    selected_nodes = inland_state_nodes + gen_nodes_selected + trans_nodes_selected + MRE_selected_nodes
    
    df = pd.read_csv('../Data_setup/10k_topology_files/10k_load.csv',header=0)
    full = list(df['Number'])
    
    excluded = [i for i in full if i not in selected_nodes]
    
    df_excluded_nodes = pd.DataFrame(excluded)
    df_excluded_nodes.columns = ['ExcludedNodes']
    f = 'Selected_nodes/excluded_nodes_' + str(NN) + '.csv'
    df_excluded_nodes.to_csv(f,index=None)
    
    df_selected_nodes = pd.DataFrame(selected_nodes)
    df_selected_nodes.columns = ['SelectedNodes']
    f = 'Selected_nodes/selected_nodes_' + str(NN) + '.csv'
    df_selected_nodes.to_csv(f,index=None)
    
    all_selected_BAs = list(df_BA_states.loc[df_BA_states['Number'].isin(selected_nodes)]['NAME'].values)
    print('Number of included BAs = {}'.format(len(set(all_selected_BAs))))
    
