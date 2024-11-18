```eval_rst
.. _search-bar:
```

Search Bar
===================

GrantNav's search bar is a powerful and flexible tool that forms the starting point for almost every exploration of grants data with GrantNav

## Text Search

When you enter a term into the search bar and click 'Search', GrantNav searches through all the grants in the database, and presents results in order of relevance - with the results that match the most words, most often, at the top.

By default, GrantNav searches all of the fields in the grant record - this includes the title and description, the names of places and geocodes, the names of funder and recipient, and any other information that the publisher of the data has provided.

To search for a particular phrase, put it in quotes in the search bar. Quotes can also help avoid unexpected results if your search term contains special characters such as dashes or brackets.

Text search isn't case-sensitive, so capital and lower-case letters will match each other; "GiRlS" matches "girls". Diacritics are ignored, so "Esmee" matches "Esmée".

GrantNav carries out stemming, so will return results for different forms of the same word; "disability" matches "disability", "disabled", etc.

On the results page, you can [refine your results](refining-results) to narrow down your search.

```eval_rst
.. admonition:: Try these examples
    :class: hint

    .. markdown::

        A single word: e.g. <code>[people](https://grantnav.threesixtygiving.org/search?text_query=people)</code>

        Multiple words: e.g. <code>[young people gardens](https://grantnav.threesixtygiving.org/search?text_query=young+people+gardens)</code> . GrantNav will first show results that contain all the words, then those which contain two of the words, and then those which contain only one.

        A phrase: e.g. <code>["frames and stonework"](https://grantnav.threesixtygiving.org/search?text_query="frames%20and%20stonework")</code>

        A specific grant: e.g. <code>["360G-wolfson-19750"](https://grantnav.threesixtygiving.org/search?text_query=%22360G-wolfson-19750%22")</code>

        Grants that are by, or that mention, a particular organisation: e.g. <code>["The Dulverton Trust"](https://grantnav.threesixtygiving.org/search?text_query=%22The+Dulverton+Trust%22)</code>

```



## AND, OR and NOT operators

The search bar allows you to specify a more constrained search by specifying combinations of words which must or must not appear.

```eval_rst
.. admonition:: Try these examples
    :class: hint

    .. markdown::

        Require each word to be found: e.g. <code>[young AND people](https://grantnav.threesixtygiving.org/search?text_query=young+AND+people)</code>

        Exclude results that contain a word: e.g. <code>[youth NOT clubs](https://grantnav.threesixtygiving.org/search?text_query=youth+NOT+clubs)</code>

```


## Searching Specific Fields

The search bar allows you to search within specific fields within the data, including all of the fields from the [360Giving Data Standard](https://standard.threesixtygiving.org/en/latest/reference/#json-format) and fields provided by specific publishers. To see which fields each publisher provides, look at a sample of the grants that they've published.

GrantNav uses the JSON field names rather than the "human-friendly" form that you'll normally see used. The conversion uses the following rules:

* Fields with a single-word name are lower case - e.g. "Title" becomes `title`
* Fields with a multi-word name are camelCase - e.g. "Award Date" becomes `awardDate`
* Colons become dots - e.g. "Beneficiary Location: Name" becomes `beneficiaryLocation.name`
* "Org" becomes `Organization` - e.g. "Funding Org: Name" becomes `fundingOrganization.name`
* "Geographic" becomes  `geo` - e.g. "Beneficiary Location:0:Geographic Code" becomes `result.beneficiaryLocation.0.geoCode`

```eval_rst
.. admonition:: Try these examples
    :class: hint

    .. markdown::

        Search the `title` field for the word 'gardens': <code>[title:gardens](https://grantnav.threesixtygiving.org/search?text_query=title:gardens)</code>

        Search the `recipientOrganization.postalCode` field for 'NW1' (where the publisher has provided this field): e.g. <code>[recipientOrganization.postalCode:NW1](https://grantnav.threesixtygiving.org/search?text_query=recipientOrganization.postalCode:NW1)</code>

        Search the `Funding Organisation:Name` field for "London Councils" (where the publisher has provided this field): <code>[fundingOrganization.name:\"London Councils\"](https://grantnav.threesixtygiving.org/search?text_query=fundingOrganization.name:%22London+Councils%22)</code>. Note that the quotes operate the same way as above - so the name has to match the phrase in order to be returned in these results.
```


```eval_rst
.. _search-ranges:
```
## Searching Ranges

The search bar allows you to search for a range of dates or values. Commonly, this is used to search by financial year rather than calendar year, or to look for specific ranges of funding values.

There are two ways of searching for a range - use whichever is easiest for you at the time!

### The TO operator

This takes the form `fieldName:[value1 TO value2]`.

Either of the values can be a wildcard `*`, which leaves that side of the range unbounded.

### Comparison operators

This uses the `< <= > >=` operators to describe a range - e.g. `amountAwarded:>1000` . To describe a bounded range using the comparison operators, use the AND keyword.

As ever, searching for a field that's optional in the standard will exclude all grants that don't have that field provided.

```eval_rst
.. admonition:: Try these examples
    :class: hint

    .. markdown::

        Award date in FY17/18: <code>[awardDate:[2017-04-01 TO 2018-03-31]](https://grantnav.threesixtygiving.org/search?text_query=awardDate:[2017-04-01+TO+2018-03-31])</code>

        Planned start date in 2016: <code>[plannedDates.startDate:>2016-01-01 AND plannedDates.startDate:<2016-12-31](https://grantnav.threesixtygiving.org/search?text_query=plannedDates.startDate:>2016-01-01+AND+plannedDates.startDate:<2016-12-31)</code>

        Planned start date in 2015 <strong>and</strong> planned end date in 2017: <code>[plannedDates.startDate:[2015-01-01 TO 2015-12-31] AND plannedDates.endDate:[2017-01-01 TO 2017-12-31]](https://grantnav.threesixtygiving.org/search?text_query=plannedDates.startDate:[2015-01-01+TO+2015-12-31]+AND+plannedDates.endDate:[2017-01-01+TO+2017-12-31])</code>. Note that the quotes operate the same way as above - so the name has to match the phrase in order to be returned in these results.

        Amount Awarded between £0 and £150: <code>[amountAwarded:[0 TO 150]](https://grantnav.threesixtygiving.org/search?text_query=amountAwarded:[0+TO+150])</code>

        Amount Applied for £1000 or more: <code>[amountAppliedFor:>=1000](https://grantnav.threesixtygiving.org/search?text_query=amountAppliedFor:>=1000)</code>

```


## Wildcards

The `?` wildcard can be used in place of an one character in text, and the `*` wildcard can be in place of any number of characters.

The `*` wildcard can also be used in place of any date or numerical value in a range, as above.

```eval_rst
.. admonition:: Try these examples
    :class: hint

    .. markdown::

        Grants containing 3-letter words that start with 'b' and end with 'g': <code>[b?g](https://grantnav.threesixtygiving.org/search?text_query=b?g)</code>

        Grants containing words that start with 'you': <code>[you*](https://grantnav.threesixtygiving.org/search?text_query=you*)</code>

```

## Fuzzy Matching

You can search for terms that are similar to, but not exactly like your search terms, using the “fuzzy” operator: `~` . To use it, put the `~` operator at the end of the term you’re looking for.

The fuzzy operator will take account of letter transposition (e.g. "youht"), letter replacement (e.g. "touth"), letters missing (e.g. "yoth") and letters added (e.g. "yoouth"), in any combination. This can be useful for taking account of mis-spellings.

Note that GrantNav already carries out stemming (ie, searching for different forms of the same word), so fuzzy matching shouldn't be used for this as the stemming is far more accurate.

Results returned from a fuzzy match should be scrutinised closely, as it can very easily include irrelevant results - for example "boys~" matches "boss".


```eval_rst
.. admonition:: Try this example
    :class: hint

    .. markdown::

        Grants containing words that are similar to youth~": <code>[youth~](https://grantnav.threesixtygiving.org/search?text_query=youth~)</code>

```

## Combining search operators

All of the search operations described here can be combined to query for a very specific set of results.

All of the search operations also are compatible with the filters on the left-hand side, so you can search, and then refine.

However, be aware that the more specific the search, the more data is excluded due to data not being provided and data quality issues (such as typos or errors in the data). To learn more about this, see [Understanding Results](understanding-results).

```eval_rst
.. admonition:: Try this example
    :class: hint

    .. markdown::

        Grants under £500 given in 2019 by funders whose name contains "Community Foundation" and whose description relates to disability: <code>[awardDate:[2019-01-01 TO 2019-12-31] AND amountAwarded:<500 AND fundingOrganization.name:"Community Foundation" AND description:disability](https://grantnav.threesixtygiving.org/search?text_query=awardDate:[2019-01-01+TO+2019-12-31]+AND+amountAwarded:<500+AND+fundingOrganization.name:"Community+Foundation"+AND+description:disability)</code>

```
