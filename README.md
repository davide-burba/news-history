# news-history


API to retrieve historical news from the web archive.

This API tool scrapes top news published in the past from major news sources.

Currently supported news sources are: 
- Reuters
- Economist
- Time
- Guardian

In the url you need to specify the `source` and the `timestamp` you are interested in. 

Timestamp can be specified with a precision up to seconds, and the returned articles will be the one corresponding to the closest available time.

These are examples of valid timestamps:
- 20210101
- 2021-01-01
- 2021-01-01-12:00:00
- 20210101120000

It is possible to specify a set of `keywords` to look for, and the api will returns only articles containing the keywords in the title.  

By using the `include` parameter you can decide if the title should contain all the keywords (`include=all`) or at least one (`include=one`).
