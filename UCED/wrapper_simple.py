# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 22:14:07 2017

@author: YSu
"""

from pyomo.opt import SolverFactory
from WECC_simple import model as m1
from pyomo.core import Var
from pyomo.core import Constraint
from pyomo.core import Param
from operator import itemgetter
import pandas as pd
import numpy as np
from datetime import datetime
import pyomo.environ as pyo
from pyomo.environ import value
import os

my_cwd = os.getcwd()

days = 365 # Max = 365

instance = m1.create_instance('WECC_data.dat')
instance.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

Solvername = 'gurobi'
Timelimit = 3600 # for the simulation of one day in seconds
# Threadlimit = 8 # maximum number of threads to use

opt = SolverFactory(Solvername)
if Solvername == 'cplex':
    opt.options['timelimit'] = Timelimit
elif Solvername == 'gurobi':           
    opt.options['TimeLimit'] = Timelimit
    
# opt.options['threads'] = Threadlimit

H = instance.HorizonHours
D = 2
K=range(1,H+1)


#Space to store results
mwh=[]
on=[]
switch=[]
flow=[]
# srsv=[]
# nrsv=[]
slack = []
vlt_angle=[]
duals=[]

df_generators = pd.read_csv('Inputs/data_genparams.csv',header=0)

#Outage
df_thermal = pd.read_csv('Inputs/thermal_gens.csv',header=0)
nucs = df_thermal[df_thermal['Fuel']=='NUC (Nuclear)']
df_loss_dict= np.load('Inputs/gen_outage_cat.npy',allow_pickle='TRUE').item()
df_losses = pd.read_csv('Inputs/west_{}_lostcap.csv'.format(my_cwd[-4:]),header=0,index_col=0)

#Line outages
df_line_outages = pd.read_csv('Inputs/line_outages.csv',header=0)

#max here can be (1,365)
for day in range(1,days+1):
    
    for z in instance.buses:
    #load Demand and Reserve time series data
        for i in K:
            instance.HorizonDemand[z,i] = instance.SimDemand[z,(day-1)*24+i]

            # instance.HorizonReserves[i] = instance.SimReserves[(day-1)*24+i]

    for z in instance.Hydro:
    #load Hydropower time series data
        instance.HorizonHydro_MAX[z] = instance.SimHydro_MAX[z,day]
        instance.HorizonHydro_MIN[z] = instance.SimHydro_MIN[z,day]
        instance.HorizonHydro_TOTAL[z] = instance.SimHydro_TOTAL[z,day]
        
    for z in instance.Solar:
    #load Solar time series data
        for i in K:
            instance.HorizonSolar[z,i] = instance.SimSolar[z,(day-1)*24+i]
    
    for z in instance.Wave:
    #load Wave time series data
        for i in K:
            instance.HorizonWave[z,i] = instance.SimWave[z,(day-1)*24+i]
    
    for z in instance.Wind:
    #load Wind time series data
        for i in K:
            instance.HorizonWind[z,i] = instance.SimWind[z,(day-1)*24+i]
    
    for z in instance.lines:
    #load line outages and limits time series data
        for i in K:
            instance.HorizonLineLimit[z,i] = instance.SimLineLimit[z,(day-1)*24+i]        
    
    for z in instance.Thermal:
    #load fuel prices for thermal generators
        instance.FuelPrice[z] = instance.SimFuelPrice[z,day]

    #Organizing outage data
    #load gen and mustrun capacity time series data
    for z in instance.Thermal:
        for i in K:
            instance.HorizonGenLimit[z,i] = instance.SimGenLimit[z,(day-1)*24+i]
    
    for z in instance.buses:
        for i in K:
            instance.HorizonMustrunLimit[z,i] = instance.SimMustrunLimit[z,(day-1)*24+i]
    
    # subtract real or historical capacity losses
    for z in instance.Gas_below_50:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Gas_below_50']/len(df_loss_dict['Gas_below_50']))
    for z in instance.Gas_50_100:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Gas_50_100']/len(df_loss_dict['Gas_50_100']))
    for z in instance.Gas_100_200:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Gas_100_200']/len(df_loss_dict['Gas_100_200']))  
    for z in instance.Gas_200_300:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Gas_200_300']/len(df_loss_dict['Gas_200_300'])) 
    for z in instance.Gas_300_400:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Gas_300_400']/len(df_loss_dict['Gas_300_400'])) 
    for z in instance.Gas_400_600:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Gas_400_600']/len(df_loss_dict['Gas_400_600'])) 
    for z in instance.Gas_600_800:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Gas_600_800']/len(df_loss_dict['Gas_600_800'])) 
    for z in instance.Gas_800_1000:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Gas_800_1000']/len(df_loss_dict['Gas_800_1000'])) 
    for z in instance.Gas_ovr_1000:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Gas_ovr_1000']/len(df_loss_dict['Gas_ovr_1000'])) 
    for z in instance.Gas_All_n_0_100:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Gas_All_n_0_100']/len(df_loss_dict['Gas_All_n_0_100']))
    for z in instance.Gas_All_n_100_200:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Gas_All_n_100_200']/len(df_loss_dict['Gas_All_n_100_200'])) 
    for z in instance.Gas_All_n_ovr_200:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Gas_All_n_ovr_200']/len(df_loss_dict['Gas_All_n_ovr_200'])) 
    for z in instance.Coal_below_50:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Coal_below_50']/len(df_loss_dict['Coal_below_50'])) 
    for z in instance.Coal_50_100:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Coal_50_100']/len(df_loss_dict['Coal_50_100'])) 
    for z in instance.Coal_100_200:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Coal_100_200']/len(df_loss_dict['Coal_100_200'])) 
    for z in instance.Coal_200_300:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Coal_200_300']/len(df_loss_dict['Coal_200_300'])) 
    for z in instance.Coal_300_400:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Coal_300_400']/len(df_loss_dict['Coal_300_400'])) 
    for z in instance.Coal_400_600:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Coal_400_600']/len(df_loss_dict['Coal_400_600'])) 
    for z in instance.Coal_600_800:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Coal_600_800']/len(df_loss_dict['Coal_600_800'])) 
    for z in instance.Coal_800_1000:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Coal_800_1000']/len(df_loss_dict['Coal_800_1000'])) 
    for z in instance.Coal_ovr_1000:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Coal_ovr_1000']/len(df_loss_dict['Coal_ovr_1000'])) 
    for z in instance.Coal_All_n_0_100:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Coal_All_n_0_100']/len(df_loss_dict['Coal_All_n_0_100'])) 
    for z in instance.Coal_All_n_100_200:
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Coal_All_n_100_200']/len(df_loss_dict['Coal_All_n_100_200'])) 
        for i in K:
            instance.HorizonGenLimit[z,i] = max(0, instance.HorizonGenLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Coal_All_n_ovr_200']/len(df_loss_dict['Coal_All_n_ovr_200'])) 

   #NEED TO ADD MUST RUN GENERATION OUTAGES     
    for z in instance.buses:
        for i in K:
            instance.HorizonMustrunLimit[z,i] = max(0,instance.HorizonMustrunLimit[z,i].value - df_losses.loc[(day-1)*24+i,'Nuclear_ovr_1000']/len(nucs))        
    
    #Organizing line outage data
    for z in instance.lines:
        for i in K:  
            instance.HorizonLineLimit[z,i] = max(0, instance.HorizonLineLimit[z,i].value - df_line_outages.loc[(day-1)*24+i-1,z])

    result = opt.solve(instance,tee=True,symbolic_solver_labels=True, load_solutions=False) ##,tee=True to check number of variables\n",
    instance.solutions.load_from(result)  
    
    print('LP')
                        

    for c in instance.component_objects(Constraint, active=True):
        cobject = getattr(instance, str(c))
        if str(c) in ['Node_Constraint']:
            for index in cobject:
                 if int(index[1]>0 and index[1]<25):
                     try:
                         duals.append((index[0],index[1]+((day-1)*24), instance.dual[cobject[index]]))
                     except KeyError:
                         duals.append((index[0],index[1]+((day-1)*24),-999))

    for v in instance.component_objects(Var, active=True):
        varobject = getattr(instance, str(v))
        a=str(v)
                  
        if a=='Theta':
            for index in varobject:
                if int(index[1]>0 and index[1]<25):
                    if index[0] in instance.buses:
                        vlt_angle.append((index[0],index[1]+((day-1)*24),varobject[index].value))
                        
        if a=='mwh':
            for index in varobject:
                
                gen_name = index[0]
                gen_heatrate = df_generators[df_generators['name']==gen_name]['heat_rate'].values[0]
                
                if int(index[1]>0 and index[1]<25):
                    
                    # fuel_price = instance.FuelPrice[z].value
                    
                    if index[0] in instance.Gas:
                        # marginal_cost = gen_heatrate*fuel_price
                        mwh.append((index[0],'Gas',index[1]+((day-1)*24),varobject[index].value))   
                    elif index[0] in instance.Coal:
                        # marginal_cost = gen_heatrate*fuel_price
                        mwh.append((index[0],'Coal',index[1]+((day-1)*24),varobject[index].value))  
                    elif index[0] in instance.Oil:
                        # marginal_cost = 0
                        mwh.append((index[0],'Oil',index[1]+((day-1)*24),varobject[index].value))   
                    elif index[0] in instance.Hydro:
                        # marginal_cost = 0
                        mwh.append((index[0],'Hydro',index[1]+((day-1)*24),varobject[index].value)) 
                    elif index[0] in instance.Solar:
                        # marginal_cost = 0
                        mwh.append((index[0],'Solar',index[1]+((day-1)*24),varobject[index].value))
                    elif index[0] in instance.Wave:
                        # marginal_cost = 0
                        mwh.append((index[0],'Wave',index[1]+((day-1)*24),varobject[index].value))    
                    elif index[0] in instance.Wind:
                        # marginal_cost = 0
                        mwh.append((index[0],'Wind',index[1]+((day-1)*24),varobject[index].value))                                            
        
        if a=='on':  
            for index in varobject:
                if int(index[1]>0 and index[1]<25):
                    on.append((index[0],index[1]+((day-1)*24),varobject[index].value))

        if a=='switch':
            for index in varobject:
                if int(index[1]>0 and index[1]<25):
                    switch.append((index[0],index[1]+((day-1)*24),varobject[index].value))
                    
        if a=='S':    
            for index in varobject:
                if index[0] in instance.buses:
                        slack.append((index[0],index[1]+((day-1)*24),varobject[index].value))

        if a=='Flow':    
            for index in varobject:
                if int(index[1]>0 and index[1]<25):
                    flow.append((index[0],index[1]+((day-1)*24),varobject[index].value))                                            

        # if a=='srsv':    
        #     for index in varobject:
        #         if int(index[1]>0 and index[1]<25):
        #             srsv.append((index[0],index[1]+((day-1)*24),varobject[index].value))

        # if a=='nrsv':    
        #     for index in varobject:
        #         if int(index[1]>0 and index[1]<25):
        #             nrsv.append((index[0],index[1]+((day-1)*24),varobject[index].value))
        
                                
        for j in instance.Dispatchable:
            if instance.mwh[j,24].value <=0 and instance.mwh[j,24].value>= -0.0001:
                newval_1=0
            else:
                newval_1=instance.mwh[j,24].value
            instance.mwh[j,0] = newval_1
            instance.mwh[j,0].fixed = True
            


    print(day)
        
vlt_angle_pd=pd.DataFrame(vlt_angle,columns=('Node','Time','Value'))
mwh_pd=pd.DataFrame(mwh,columns=('Generator','Type','Time','Value'))
# on_pd=pd.DataFrame(on,columns=('Generator','Time','Value'))
# switch_pd=pd.DataFrame(switch,columns=('Generator','Time','Value'))
# srsv_pd=pd.DataFrame(srsv,columns=('Generator','Time','Value'))
# nrsv_pd=pd.DataFrame(nrsv,columns=('Generator','Time','Value'))
slack_pd = pd.DataFrame(slack,columns=('Node','Time','Value'))
flow_pd = pd.DataFrame(flow,columns=('Line','Time','Value'))
duals_pd = pd.DataFrame(duals,columns=['Bus','Time','Value'])

#to save outputs
mwh_pd.to_parquet('Outputs/mwh.parquet', index=False)
vlt_angle_pd.to_parquet('Outputs/vlt_angle.parquet', index=False)
# on_pd.to_parquet('Outputs/on.parquet', index=False)
# switch_pd.to_parquet('Outputs/switch.parquet', index=False)
# srsv_pd.to_parquet('Outputs/srsv.parquet', index=False)
# nrsv_pd.to_parquet('Outputs/nrsv.parquet', index=False)
slack_pd.to_parquet('Outputs/slack.parquet', index=False)
flow_pd.to_parquet('Outputs/flow.parquet', index=False)
duals_pd.to_parquet('Outputs/duals.parquet', index=False)




