Downloads
============================

GrantNav offers a range of data exports as CSV or JSON files:

* The entire grants data set
* Search results
* Grants per region, district, funder and recipient
* Summary data by funder

## What is included in the GrantNav export files?

### Grants Exports

The JSON files of grants contain all of the data supplied in the original data (both fields from the standard, and any extra fields included by the publisher), plus the [additional data added by the 360Giving pipeline](additional-fields).

The CSV files of grants contain all of the required fields from the 360Giving standard, the most commonly-used optional fields from the standard, plus some commonly-used fields from the data added by the 360Giving pipeline. Columns may be entirely blank if no grant in your download uses a particular field; individual rows may have blank fields if the source data doesn't contain that field.

Grants export files use the [360Giving Standard](https://standard.threesixtygiving.org/en/latest/); refer to the standard website to understand the meaning and contents of the fields.

Note that export files can be very large - in particular the whole dataset is several hundred MB, and large search results can be a similar size. Refining your search or splitting up your export can help, but be aware of the constraints around [refining search results](refining-results)

The entire data set can be exported as [JSON](http://grantnav.threesixtygiving.org/search.json) or [CSV](http://grantnav.threesixtygiving.org/search.csv)


```eval_rst
.. _funder-recipient-summary-fields:
```

### Funder & Recipient Summary Exports

The funder and recipient summary pages offer statistics about the grants given to/by each funder and recipient in GrantNav. These statistics can be exported. The JSON and CSV files for the recipient and funder pages contain all of the fields from the tables in GrantNav, plus an extra column containing the organisation ID:

```eval_rst
.. list-table::
    :header-rows: 1
    :widths: 1 3

    * - Field
      - Description
    * - Funder / Recipient
      - Funder or recipient name
    * - Funder Id / Recipient Id
      - Identifier code of the funder or recipient
    * - Grants
      - Number of grants made by/to the funder or recipient
    * - Total
      - Total value of all grants made by/to the funder or recipient
    * - Average
      - Average value of a grant made by/to the funder or recipient
    * - Largest
      - Value of the largest grant made by/to the funder or recipient
    * - Smallest
      - Value of the smallest grant made by/to the funder or recipient

```



```eval_rst
.. _additional-fields:
```

## Fields added by the 360Giving Datastore pipeline

The [360Giving Datastore](https://www.threesixtygiving.org/data/360giving-datastore/) carries out an augmentation process, in order to help make the data easier to use in multiple ways. GrantNav uses the datastore for its data supply. These fields are available in the JSON; to understand the fields that are available, click the "Show Additional Data" button on the grant page for some of the grants that you'll be downloading.
