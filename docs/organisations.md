```eval_rst
.. _organisations:
```

Organisations
=========================

GrantNav provides a view of all the grants known to be associated with a single organisation. Because one organisation can have lots of different variations of their name (“R S P B”, “Royal Society for the Protection of Birds”, “The RSPB”, and so on), and different organisations can have the same or similar names, GrantNav uses the organisation identifiers (Org IDs) provided by publishers in the 360Giving Data Standard fields Recipient Org:Identifier and Funding Org:Identifier to distinguish between different organisations, and decide what counts as a single organisation.

Using Org IDs in the published 360Giving data, GrantNav attempts to group all the grants associated with a single organisation into a single view, however there are circumstances when that isn’t possible. This means that when exploring organisations in GrantNav, there may be more than one record for the same organisation.

The following guidance explains further how organisations are identified in 360Giving data and how GrantNav handles this information, explaining why you might see multiple records for the same organisation.

## About organisation identifiers in 360Giving data

In 360Giving data there are two parts to an Org ID:
- **A list code**: a prefix that describes the list the identifier is taken from.
- **An identifier** taken from that list.

```eval_rst
.. admonition:: For example
    :class: hint

    .. markdown::

        A charity registered in England and Wales with the Charity Commission of England and Wales, with the charity number '1164883' will use a list code prefix of ``GB-CHC``. This gives an unique organisation identifier of ``GB-CHC-1164883``
```

Many organisations in the UK have some sort of official registration number that can be used as an identifier, for example registered charity or company numbers. When funders include Org IDs using official registration numbers in their 360Giving data, it makes it possible to see when a recipient has been awarded grants by multiple funders. It also allows grant data to be linked or combined with information taken from official registers.

Some organisations have more than one official registration number: they might be a charity and a company, or a charity and an educational establishment. If different publishers have identified the same organisation using different official registration numbers GrantNav is able to match them together and group all the grants associated into a single view.

## Organisations without official registration numbers

Not all organisations in GrantNav are identified using official registration numbers. Some organisations, such as small unregistered groups, do not have any type of official registration number that could be used to create an organisation identifier. Sometimes a funder does not include the official registration numbers for an organisation in their 360Giving data because they don’t collect this information.

When there is no official registration number available for an organisation, the funder sharing the data must use an internal identifier to create an Org ID instead, using a reference from their own data and their publisher prefix, which starts **360G**.

In these cases, GrantNav is not able to group the grants published by different funders together and each different Org ID starting 360G will have a single view. This means a single organisation could have multiple pages on GrantNav.

## About organisation names in 360Giving data

In order to provide a consistent experience, and because one organisation can have lots of different variations of their name, GrantNav uses the names taken from official sources, such as the UK charity and company registers for organisation page titles and filters. When an organisation is a publisher of 360Giving data the name will be taken from the 360Giving Data Registry instead. All versions of an organisation’s name, used in the data and taken from official sources, are displayed on the organisation page.

## Organisation roles in GrantNav

An organisation can appear in GrantNav as a Funder, a Publisher, or a Recipient or any combination of those roles.
- An organisation is a **Funder** when their details appear in 360Giving data in the Funding Org:Name and Funding Org:Identifier fields.
- An organisation is a **Recipient** when their details appear in 360Giving data in the Recipient Org:Name and Recipient Org:Identifier fields.
- An organisation is a **Publisher** when their name appears on the 360Giving Data Registry, and they can be identified by their publisher name and unique 360Giving Publisher prefix which starts **360G**.

In most cases the Publisher of 360Giving data is also the Funder that appears in the data. However it is possible for a Publisher to publish grants data on behalf of a different Funder, alongside its own grants. It is also possible for a Publisher to not be a Funder and solely publish grants data on behalf of others.

A Funder/Publisher might also appear as a Recipient of grants.
