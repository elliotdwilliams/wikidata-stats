# wikidata-stats

A simple command line tool for getting statistics about items edited and created in [Wikidata](https://www.wikidata.org/wiki/Wikidata:Main_Page).  The script uses the [MediaWiki API](https://www.mediawiki.org/wiki/API:Query) to get Wikidata contributions by a given user for a specified date range.

This tool was created specifically to help with gathering statistics for the [PCC EMCO Wikidata Community of Practice](https://www.wikidata.org/wiki/Wikidata:WikiProject_PCC_EMCO_Wikidata_CoP/Statistics).

## Requirements

This tool was written in Python 3 (specifically, version 3.14.8).  Required libraries are listed in the requirements.txt file.

## Using the tool

When you run the script, it will prompt you to supply:
1. Wikidata username
2. Start date of the period you want statistics for (YYYY-MM-DD)
3. End date of the period you want statistics for (YYYY-MM-DD)

The script will then get all Wikidata contributions for that user during the specified time period.  For each item edited, it will attempt to determine if the item was a newly-created item or a pre-existing item that was edited.  Lists of new and edited items are deduplicated, so each item only shows up in one list.
- "Created" items are determined based on the presence of the "new" key in the API response or "new" in the item flags, or based on the contribution's parentid (the ID of the previous revision) being 0.

Two files will be output:
1. Overall report, including the username and dates searched, and the number of items created and edited
2. List of items edited, including the QID of each item and whether it was created or edited

## Acknowledgements

This script is an adaptation of the [wikidata-stats project](https://github.com/enarda/wikidata-stats/tree/main) by enarda.

*This project is not affiliated with or endorsed by the Wikimedia Foundation.*

## Future Enhancements

I hope to further develop this tool:
1) Generate stats for multiple users in one go
2) Include additional information in the export list (e.g. item label, instance of value)