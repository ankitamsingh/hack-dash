We will be working on a quick ai project for a hackathon for a bank. We will be creating a chatbot for backend admin to help them with stats, trends and predictions. Few things to take note.

1. We will not be able to ping csv, excel or live database or any database all the data should be in the faiss 
2. We do not need row wise data as its stats, trends predictions and totals we can save the data based on the questions i will provide 
3. We will flan t5 base for query conversion when userr enters the query we will pass to flan to make the query refined and then we will pass it to our faiss and then once we get the answer we will pass it to flan enrich the answer and show it to the admins in the chatbot.

How we will be working 

1. The folders with files are 
Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        03-06-2025     04:55                data
d-----        03-06-2025     04:54                faiss_index
d-----        03-06-2025     04:54                scripts
-a----        02-06-2025     07:34          15669 Question and answer.docx


    Directory: F:\Projects\AIModel\demo\data


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        03-06-2025     04:55                Main_Tables
d-----        03-06-2025     04:55                Supporting_Tables


    Directory: F:\Projects\AIModel\demo\data\Main_Tables


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        03-06-2025     04:55                account
d-----        03-06-2025     04:55                customer-login
d-----        03-06-2025     04:55                payment
d-----        03-06-2025     04:55                transaction


    Directory: F:\Projects\AIModel\demo\data\Main_Tables\account


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        01-06-2025     19:41         567582 accnt_party.csv
-a----        01-06-2025     19:41         789815 account_hdr.csv


    Directory: F:\Projects\AIModel\demo\data\Main_Tables\customer-login


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        01-06-2025     19:41         555951 customer_login.csv


    Directory: F:\Projects\AIModel\demo\data\Main_Tables\payment


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        03-06-2025     04:55                Internal-payment
-a----        01-06-2025     00:43        1603578 accnt_dtl_c.csv
-a----        03-06-2025     00:40         942113 accnt_dtl_mapped_from_stmt_fixed.xlsx
-a----        01-06-2025     00:43         558891 stmt_dtl.csv
-a----        03-06-2025     00:13         455767 stmt_dtl_updated_consistent_dates.xlsx


    Directory: F:\Projects\AIModel\demo\data\Main_Tables\payment\Internal-payment


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        02-06-2025     23:58        1419388 movement_20000.xlsx
-a----        03-06-2025     00:03         357131 payment_movement_5000_full_records.xlsx


    Directory: F:\Projects\AIModel\demo\data\Main_Tables\transaction


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        01-06-2025     21:51         826764 transactions.csv
-a----        03-06-2025     00:49         625856 transactions_updated_dates.xlsx


    Directory: F:\Projects\AIModel\demo\data\Supporting_Tables


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        03-06-2025     04:55                account
d-----        03-06-2025     04:55                customer-login
d-----        03-06-2025     04:55                payment
d-----        03-06-2025     04:55                transaction


    Directory: F:\Projects\AIModel\demo\data\Supporting_Tables\account


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        01-06-2025     19:41            538 accnt_role_type_cd.csv
-a----        01-06-2025     19:41            503 accnt_status_cd.csv
-a----        01-06-2025     19:41           1387 account_close_reasons_with_mod_user.csv
-a----        01-06-2025     19:41            441 account_open_reason_data.csv
-a----        01-06-2025     19:41           1627 prtnr_cd.csv


    Directory: F:\Projects\AIModel\demo\data\Supporting_Tables\customer-login


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        01-06-2025     19:41            231 login_status_data.csv


    Directory: F:\Projects\AIModel\demo\data\Supporting_Tables\payment


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        03-06-2025     04:55                internal-payment


    Directory: F:\Projects\AIModel\demo\data\Supporting_Tables\payment\internal-payment


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        02-06-2025     19:56           6083 money_mvmnt_status_cd.xlsx
-a----        01-06-2025     06:05           1958 money_mvmnt_status_reason_full.csv
-a----        02-06-2025     20:00           5696 money_mvmnt_subsc_optn_cd.xlsx
-a----        02-06-2025     22:45           5507 money_mvmnt_type.xlsx


    Directory: F:\Projects\AIModel\demo\data\Supporting_Tables\transaction


Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        01-06-2025     19:26            103 tran_cat_cd.csv
-a----        01-06-2025     19:24            434 Tran_cd.csv

2. once you understand the path and save them i will update you all the csv and demo tables from teh data folder in a zip once you take note all the data and columns and supporting ids and id descriptions and save them for later reference

3. I will give you some example questions that we need to get correct and accurate answers

4. Once the above things are done we will start working on the code for build faiss and query with models 

5. We will implement the code one data folder at a time to make it more cleaner and without errors. (ie. we will start with account folder in main and supporting table along with all questions from the account folder and then we will keep going on folder at a time.) small note here we only need one response like how we will show in hatbbot and not multiple results 

6. Once we are done with all the folder and the query with model is responding correctly we will move to steamlit for webapp.



