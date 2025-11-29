start_all.sh

** Refresh the URL if yo need . Ideally to refresh the URL once a Month to make sure you have upto date list of stocks belongs to particler URL .for market_index url start the http server on 8000 first by coming into project root dir .
python3 -m http.server 8000
1. Refresh the mapping first . This will map the symbol names with NSE returned SYmbol to download the correct stock/data.This is Mendatory if You are refreshing the URL 

python DataLoadManagement.py refresh-mappings

2. To check the List of avilable Indices for which you can run the downloads 
python DataLoadManagement.py list-indices

📊 Available Indices (8):
==================================================
 1. MARKET INDEXES (32 symbols)
 2. NIFTY 200 (200 symbols)
 3. NIFTY 500 (501 symbols)
 4. NIFTY100 (100 symbols)
 5. NIFTY150 (150 symbols)
 6. NIFTY50 (50 symbols)
 7. NIFTYMID150 (150 symbols)
 8. NIFTYSMALL250 (251 symbols)


3. Download the Data based on option you want .
python DataLoadManagement.py download-index "NIFTY 500" [options]

Options:
--start-date YYYY-MM-DD    # Custom start date (default: 2005-01-01)
--end-date YYYY-MM-DD      # Custom end date (default: current date)
--force-refresh           # Force download even if recent data exists
--max-concurrent N        # Number of concurrent downloads (default: 5)

python DataLoadManagement.py download-index "MARKET INDEXES" --force-refresh

python DataLoadManagement.py download-index "NIFTY 500" --force-refresh 

python DataLoadManagement.py download-stock HDFCBANK --force-refresh

4. Run the Indicator calculations to calculate the Score .

5. If want to delete price data for an existing stock

 python DataLoadManagement.py delete-stock 'NIFTY50 EQL Wgt' --confirm

#########Screener################
/media/guru/Data/workspace/market-hunt/frontend/pages/1_Stock_Screener.py
streamlit run 1_stock_screener.py
############### 2020-2025###############

######################## Nifty 50 ################################
#### Weekly .5 out of N50 Skewed
184 |  264
#### Monthy .5 out of N50 Skewed
268 |  288

###### Buy TOP 3 222D-PROC-MONTHLY###
261|280
###### Buy TOP 5 222D-PROC-MONTHLY###
283|303
###### Buy TOP 7 222D-PROC-MONTHLY###
267|286
###### Buy TOP 10 222D-PROC-MONTHLY###
247|265

######################## Nifty 100 ######################################
#### Weekly .5 out of N100 Skewed
506 |  642
#### Monthy .5 out of N100 Skewed
702 |  741
######################## Nifty 100 ######################################
#### Monthy .10 out of N100 Skewed
716 |  



###### Buy TOP 10 222D-PROC-MONTHLY--->66DaysROC###
777 | 813------>722|760
###### Buy TOP 7 222D-PROC-MONTHLY###
1000|1050
###### Buy TOP 5 222D-PROC-MONTHLY###
900|950
###### Buy TOP 3 222D-PROC-MONTHLY###
700|750
###### Buy TOP 2 222D-PROC-MONTHLY###
840|885
###### Buy TOP 1 222D-PROC-MONTHLY###
1950|2000

######################## Nifty 101-250 #############################
#### Weekly .10 out of N150 Skewed
282 |  362
#### Monthy .10 out of N150 Skewed
945 |  982
###### Buy TOP 10 222D-PROC-MONTHLY###
983|1023
###### Buy TOP 7 222D-PROC-MONTHLY###
776|812
###### Buy TOP 5 222D-PROC-MONTHLY###
1088|1163
###### Buy TOP 3 222D-PROC-MONTHLY###
1072|1120


######################## Nifty 251-500 ##########################


#### Monthly .15 out of N250 Skewd
881 | 919
###### Buy TOP 15 222D-PROC-MONTHLY###
1006|1061
###### Buy TOP 20 222D-PROC-MONTHLY###
900|930
######################### Nifty 500 #######

#### Monthly .30 out of N500 Skewd
992 | 1032


############# Sweet-Spot Holding ######
Nifty top 50 --> 4-6    peaked at 5-6
Nifty top 100--> 4-8    peaked at 4-5
Nifty top 200-->10-12   peaked at 8-9
Nifty 100-250-->10-12   peaked at 10
Nifty 250-500-->8-12    peaked at 

Nifty total 500-20-27    peaked at 

