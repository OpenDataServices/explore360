```eval_rst
.. _refining-results:
```

Filters
================

On the search results page, there are a number of filters down the left-hand side. These refine your search.

For each filter, clicking on a value will filter the search results to contain only the grants that match that criterion. To select multiple criteria, click on each relevant value. For example, to see grants made in both GBP and USD, click on GBP, and then USD. Note that the page updates after each click, so a short delay is advisable.

The numbers in brackets next to the values show the number of grants in the search results that match that criterion.

## Filter Reference

```eval_rst
.. list-table::
  :header-rows: 1
  :widths: 1 2 2

  * - GrantNav filter
    - 360Giving Data Standard field
    - Notes
  * - Currency
    - Currency
    -            
  * - Amount Awarded (GBP)
    - Amount Awarded
    - Using this filter will exclude all non-GBP grants from the search results
  * - Award Date
    - Award Date
    - The year values are calendar year, not fiscal/financial year, or a range can be selected in the From/To months. See :ref:`search-ranges` for how to search between specific dates.
  * - Recipient Region
    - This filter is derived from 360Giving data by GrantNav
    - See also: :doc:`./locations`
  * - Recipient District
    - This filter is derived from 360Giving data by GrantNav
    - See also: :doc:`./locations`
  * - Funding Organisations
    - Funding Org:Name
    - Values are taken from the data and will change if the funder name changes.
  * - Recipient Organisations
    - Recipient Org:Name
    - See also: :doc:`./organisations`
  * - Funding Organisation Type
    - This filter is derived from 360Giving data by GrantNav
    - Derived from organisation identifiers
  * - Grant Programme Title
    - Grant Programme Title
    - Values are taken from the data
  * - Type of Recipient
    - Recipient Org:Name or Recipient Ind:Name
    - Derived from whether the Recipient Organisation or Individual fields are used in the data
  * - Grant Type
    - For Regrant
    - Derived from whether the For Regrant field was used or not in the data
```
