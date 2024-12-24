special_instruction = '''
This is a website that publish auto sales data by manufacturer in China. 
There are numerous links on the initial landing page. Each link links to separate webpage with sales data of a specific auto manufacturer, 
broken out by models, for a specific month. You should extract the sales data of the manufacturer's models and the total sales for that month. 
Only scrape links on this page under 厂商销量, and before [第一页]. 
when url path is relative, assume it's from domain http://www.myhomeok.com/. do NOT explore other pages outside of domain, especially ecar168.cn. 
Do NOT translate data to english."
'''