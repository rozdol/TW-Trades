from lightweight_charts import Chart
import pandas as pd
import numpy as np
from datetime import datetime
import pickle

def get_trades():

	# read file into Dataframe
	df_trades=pd.read_excel(f'Trades.xlsx')

	# convert time filed into DateTime type
	df_trades['timestamp'] = pd.to_datetime(df_trades['Trade Date/Time'], format='%Y-%m-%d, %H:%M:%S')

	# sort trades by time
	df_trades=df_trades.sort_values(by=['timestamp'], ascending=[True])

	# convert string amounts into real numbers
	df_trades['Price'] = df_trades['Price'].str.replace(',', '').astype(float)
	df_trades['Notional Value'] = df_trades['Notional Value'].str.replace(',', '').astype(float)

	# Shift Time Zone from NYT to local UTC+3
	utc = np.timedelta64(4+3, 'h') 
	df_trades['timestamp'] = df_trades['timestamp'] + utc

	# Calculate Profit and Loss values
	df_trades['Position']=df_trades['Quantity'].cumsum()
	df_trades['PL']=df_trades['Notional Value'].cumsum()
	df_trades.loc[df_trades['Position']!=0,['PL']]=np.nan
	df_trades['PL']=df_trades['PL'].ffill()
	df_trades['PL']=df_trades['PL'].fillna(0)
	df_trades['Gain']=df_trades['PL']-df_trades['PL'].shift()
	df_trades['Gain']=df_trades['Gain'].fillna(0)
	df_trades['NetPL']=df_trades['PL']+df_trades['Comm']+df_trades['Fee']

	# create an index to merge with other OHLC dataframe
	df_trades['time'] = pd.to_datetime(df_trades['timestamp'])
	df_trades.set_index('time', inplace=True)
	return df_trades

def calculate_npl(df):
    return pd.DataFrame({
        'time': df.index,
        f'NetPL': df['NetPL']
    }).dropna()

if __name__ == '__main__':

	# read Trades data
	df_trades=get_trades()

	# read ohlc data
	df_bars=pd.read_csv('ohlc.csv', parse_dates=['time'])
	df_bars.set_index('time',inplace=True)

	# merge ohlc data with trades
	df_merged = pd.merge_asof( df_bars, df_trades, left_index=True, right_index=True, direction='backward')

	# Get Cart Instance
	chart = Chart(toolbox=True,inner_width=1, inner_height=0.8)
	chart.time_scale(visible=False)
	chart.topbar.textbox('symbol', 'MNQH4')
	# load ohlc data to the chart
	chart.set(df_bars)

	# get npl dataframe for PL subchart
	npl_df = calculate_npl(df_merged)

	# create subchart for PL
	chart2 = chart.create_subchart(width=1, height=0.3, sync=True,position='bottom')

	# add data to PL subchart
	line = chart2.create_line(name='NetPL', color='blue')
	line.set(npl_df)


	start_points=[] # list of strting points to draw trend lines
	#iterate tfrough trades to plot trading markers
	for row in df_trades.itertuples(): 
	    time=row[14]
	    action=row[6]
	    qty=row[7]
	    price=row[8]
	    gain=row[17]


	    if gain==0.0:
	        label= f'{qty}'
	        start_points.append({'time':time,'value':price,'qty':qty})
	    else:
	        label=f'{qty} / {gain}'
	        for point in start_points:
	            if gain>0:
	                line_color = '#008000'
	                chart.marker(time, 'inside', 'circle', '#7bfc74', f'+{gain}')
	            else:
	                line_color = '#bb0000'
	                chart.marker(time, 'inside', 'square', '#ff8888', f'{gain}')
	                
	            chart.trend_line(start_time=point['time'], 
	        		start_value=point['value'], 
	        		end_time=time, 
	        		end_value=price, 
	        		line_color=line_color, 
	        		width=point['qty']*2, 
	        		style='solid', 
	        		round=False)
	        start_points=[]

	    if action=='BUY':
	        chart.marker(time, 'below', 'arrow_up', '#7bfc74', f'{qty}')
	    else:
	        chart.marker(time, 'above', 'arrow_down', '#ff8888',f'{qty}')

	# load persistent drawings
	chart.toolbox.import_drawings('drawings.json')
	chart.toolbox.load_drawings(chart.topbar['symbol'].value) 
	chart.toolbox.save_drawings_under(chart.topbar['symbol'])  
	chart.show(block=True)
	# save persistent drawings on exit
	chart.toolbox.export_drawings('drawings.json')  
	chart.exit()