```eval_rst
.. _locations:
```

Understanding Location
==================================

Understanding where a grant is located is one of the most common tasks that GrantNav is used for, and where there is potential for misunderstanding.

The [360Giving Data Standard](https://standard.threesixtygiving.org/en/latest/reference/) doesn't require that grants contain location data. This is because this isn't data that all grantmakers keep, and it's not always relevant – for example, if a grant relates to policy or research.

If a grant doesn't have any location information, then it won't show up in searches using the **Locations search mode** of the [Search Bar](https://help.grantnav.threesixtygiving.org/en/latest/search_bar/#search-bar), or when using the **Geography filters** on the search results page. Only UK locations can be searched and filtered using these location functions. To search for locations outside of the UK, use the 'All grant fields' search mode of the Search Bar.

When a grant does include location information, in the form of a postcode or [ONS Geographic Codes](https://geoportal.statistics.gov.uk/), GrantNav uses this data to power its Location functions, populating the name and geocodes of the Ward, District, County (including Unitary Authorities) and Region or UK Country that the provided location is in, where possible.

The **Geography filters** in the left-hand side use the location data to allow filtering by UK Country and English Region, by County or by District.

The **Locations search mode** of the Search Bar allows searches by UK Country and English Region, County, and District and Ward names or geocodes.

The UK Country and English Region name, County and District and Ward names and geocode data is also included in GrantNav search result downloads in fields labelled “Additional data”.

GrantNav's **Locations search mode** is based on the names or geocodes from official ONS sources, so when searching for a place’s name, it won't provide results that are geographically near (or commonly considered to be part of) the place searched for, or distinguish between places that have the same name, or partial name. However, entering the ONS geocode into the Location search will provide an exact match and exclude places with the same name.

## Best Available Location and Recipient vs Grant Location

The 360Giving Data Standard allows publishers to include both **Recipient Location** (the place where the Recipient Organisation is based) and **Grant Location** data (the place where the funded activity is taking place, called Beneficiary location in the Standard and in GrantNav Downloads). While over two thirds of publishers share some form of Recipient Location, funders find it more challenging to determine and record Grant Location information. As a result, only one third publish Grant Location data that can be used by GrantNav. You can learn more about how many publishers and the proportion of grants with Recipient location and Grant location in our [Quality Dashboard](https://qualitydashboard.threesixtygiving.org/alldata).

Because a Grant Location usually provides a more accurate way to answer the question 'Where do grants go?’ than a Recipient location, the Location search bar and filters use the 'Best Available' location by default, which returns either Grant Location or Recipient Location data shared by publishers, with priority given to Grant Location where both are available. In addition, it is possible to switch the Geography filters to return results based on Recipient lcations only or Grant Locations only, where available. Please note however that the search results for each grant only display the Best Available Region and District.
