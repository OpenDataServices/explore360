from collections import OrderedDict

grants_csv = OrderedDict([
    ("Identifier", "result.id"),
    ("Title", "result.title"),
    ("Description", "result.description"),
    ("Currency", "result.currency"),
    ("Amount Applied For", "result.amountAppliedFor"),
    ("Amount Awarded", "result.amountAwarded"),
    ("Amount Disbursed", "result.amountDisbursed"),
    ("Award Date", "result.awardDateDateOnly"),
    ("URL", "result.recipientOrganization.0.url"),

    ("Planned Dates:Start Date", "result.plannedDates.0.startDateDateOnly"),
    ("Planned Dates:End Date", "result.plannedDates.0.endDateDateOnly"),
    ("Planned Dates:Duration (months)", "result.plannedDates.0.duration"),
    ("Actual Dates:Start Date", "result.actualDates.0.startDate"),
    ("Actual Dates:End Date", "result.actualDates.0.endDateDateOnly"),
    ("Actual Dates:Duration (months)", "result.actualDates.0.duration"),

    ("Recipient Org:Identifier", "result.recipientOrganization.0.id"),
    ("Recipient Org:Name", "result.recipientOrganization.0.name"),
    ("Recipient Org:Charity Number", "result.recipientOrganization.0.charityNumber"),
    ("Recipient Org:Company Number", "result.recipientOrganization.0.companyNumber"),
    ("Recipient Org:Postal Code", "result.recipientOrganization.0.postalCode"),
    ("Recipient Org:Location:0:Geographic Code Type", "result.recipientOrganization.0.location.0.geoCodeType"),
    ("Recipient Org:Location:0:Geographic Code", "result.recipientOrganization.0.location.0.geoCode"),
    ("Recipient Org:Location:0:Name", "result.recipientOrganization.0.location.0.name"),
    ("Recipient Org:Location:1:Geographic Code Type", "result.recipientOrganization.0.location.1.geoCodeType"),
    ("Recipient Org:Location:1:Geographic Code", "result.recipientOrganization.0.location.1.geoCode"),
    ("Recipient Org:Location:1:Name", "result.recipientOrganization.0.location.1.name"),
    ("Recipient Org:Location:2:Geographic Code Type", "result.recipientOrganization.0.location.2.geoCodeType"),
    ("Recipient Org:Location:2:Geographic Code", "result.recipientOrganization.0.location.2.geoCode"),
    ("Recipient Org:Location:2:Name", "result.recipientOrganization.0.location.2.name"),

    ("Recipient Individual Id", "result.recipientIndividual.id"),
    ("Recipient Individual Details:Primary Grant Reason", "result.toIndividualsDetails.primaryGrantReason"),
    ("Recipient Individual Details:Secondary Grant Reason", "result.toIndividualsDetails.secondaryGrantReason"),
    ("Recipient Individual Details:Grant Purpose", "result.toIndividualsDetails.grantPurpose"),

    ("Funding Org:Identifier", "result.fundingOrganization.0.id"),
    ("Funding Org:Name", "result.fundingOrganization.0.name"),
    ("Funding Org:Postal Code", "result.fundingOrganization.0.postalCode"),
    ("Funding Org:Charity Number", "result.fundingOrganization.0.charityNumber"),
    ("Funding Org:Company Number", "result.fundingOrganization.0.companyNumber"),


    ("Grant Programme:Code", "result.grantProgramme.0.code"),
    ("Grant Programme:Title", "result.grantProgramme.0.title"),
    ("Grant Programme:URL", "result.grantProgramme.0.url"),

    ("Regrant Type", "result.regrantType"),

    ("Funding Type Title", "result.fundingType.0.title"),

    ("Beneficiary Location:0:Name", "result.beneficiaryLocation.0.name"),
    ("Beneficiary Location:0:Country Code", "result.beneficiaryLocation.0.countryCode"),
    ("Beneficiary Location:0:Geographic Code", "result.beneficiaryLocation.0.geoCode"),
    ("Beneficiary Location:0:Geographic Code Type", "result.beneficiaryLocation.0.geoCodeType"),
    ("Beneficiary Location:1:Name", "result.beneficiaryLocation.1.name"),
    ("Beneficiary Location:1:Country Code", "result.beneficiaryLocation.1.countryCode"),
    ("Beneficiary Location:1:Geographic Code", "result.beneficiaryLocation.1.geoCode"),
    ("Beneficiary Location:1:Geographic Code Type", "result.beneficiaryLocation.1.geoCodeType"),
    ("Beneficiary Location:2:Name", "result.beneficiaryLocation.2.name"),
    ("Beneficiary Location:2:Country Code", "result.beneficiaryLocation.2.countryCode"),
    ("Beneficiary Location:2:Geographic Code", "result.beneficiaryLocation.2.geoCode"),
    ("Beneficiary Location:2:Geographic Code Type", "result.beneficiaryLocation.2.geoCodeType"),
    ("Beneficiary Location:3:Name", "result.beneficiaryLocation.3.name"),
    ("Beneficiary Location:3:Country Code", "result.beneficiaryLocation.3.countryCode"),
    ("Beneficiary Location:3:Geographic Code", "result.beneficiaryLocation.3.geoCode"),
    ("Beneficiary Location:3:Geographic Code Type", "result.beneficiaryLocation.3.geoCodeType"),
    ("Beneficiary Location:4:Name", "result.beneficiaryLocation.4.name"),
    ("Beneficiary Location:4:Country Code", "result.beneficiaryLocation.4.countryCode"),
    ("Beneficiary Location:4:Geographic Code", "result.beneficiaryLocation.4.geoCode"),
    ("Beneficiary Location:4:Geographic Code Type", "result.beneficiaryLocation.4.geoCodeType"),
    ("Beneficiary Location:5:Name", "result.beneficiaryLocation.5.name"),
    ("Beneficiary Location:5:Country Code", "result.beneficiaryLocation.5.countryCode"),
    ("Beneficiary Location:5:Geographic Code", "result.beneficiaryLocation.5.geoCode"),
    ("Beneficiary Location:5:Geographic Code Type", "result.beneficiaryLocation.5.geoCodeType"),
    ("Beneficiary Location:6:Name", "result.beneficiaryLocation.6.name"),
    ("Beneficiary Location:6:Country Code", "result.beneficiaryLocation.6.countryCode"),
    ("Beneficiary Location:6:Geographic Code", "result.beneficiaryLocation.6.geoCode"),
    ("Beneficiary Location:6:Geographic Code Type", "result.beneficiaryLocation.6.geoCodeType"),
    ("Beneficiary Location:7:Name", "result.beneficiaryLocation.7.name"),
    ("Beneficiary Location:7:Country Code", "result.beneficiaryLocation.7.countryCode"),
    ("Beneficiary Location:7:Geographic Code", "result.beneficiaryLocation.7.geoCode"),
    ("Beneficiary Location:7:Geographic Code Type", "result.beneficiaryLocation.7.geoCodeType"),
    ("From An Open Call?", "result.fromOpenCall"),
    # ("#comment The following fields are not in the 360 Giving Standard and are added by GrantNav.", ""),
    # Additional data
    ("Data Source", "dataset.distribution.0.downloadURL"),
    ("Publisher:Name", "dataset.publisher.name"),

    ("Best Available Recipient Region (additional data)", "result.additional_data.recipientRegionName"),
    ("Best Available Recipient District (additional data)", "result.additional_data.recipientDistrictName"),
    ("Best Available Recipient District Geographic Code (additional data)", "result.additional_data.recipientDistrictGeoCode"),
    ("Best Available Recipient Ward (additional data)", "result.additional_data.recipientWardName"),
    ("Best Available Recipient Ward Geographic Code (additional data)", "result.additional_data.recipientWardNameGeoCode"),

    ("Recipient Region (additional data)", "result.additional_data.GNRecipientOrgRegionName"),
    ("Recipient Region Geographic code (additional data)", "result.additional_data.GNRecipientOrgRegionGeoCode"),

    ("Recipient District (additional data)", "result.additional_data.GNRecipientOrgDistrictName"),
    ("Recipient District Geographic code (additional data)", "result.additional_data.GNRecipientOrgDistrictGeoCode"),

    ("Beneficiary Region (additional data)", "result.additional_data.GNBeneficiaryRegionName"),
    ("Beneficiary Region Geographic code (additional data)", "result.additional_data.GNBeneficiaryRegionGeoCode"),

    ("Beneficiary District (additional data)", "result.additional_data.GNBeneficiaryDistrictName"),
    ("Beneficiary District Geographic code (additional data)", "result.additional_data.GNBeneficiaryDistrictGeoCode"),

    ("Retrieved for use in GrantNav (additional data)", "dataset.datagetter_metadata.datetime_downloaded"),
    ("Funding Org: Org Type (additional data)", "result.additional_data.TSGFundingOrgType"),
    ("Funding Org: Canonical Org ID (additional data)", "result.additional_data.GNCanonicalFundingOrgId"),
    ("Funding Org: Canonical Name (additional data)", "result.additional_data.GNCanonicalFundingOrgName"),
    ("Type of Recipient", "result.additional_data.TSGRecipientType"),
    ("Recipient Org: Date Registered (additional data)", "result.additional_data.recipientOrgInfos.0.dateRegistered"),
    ("Recipient Org: Date Removed (additional data)", "result.additional_data.recipientOrgInfos.0.dateRemoved"),
    ("Recipient Org: Org ID(s) (additional data)", "result.additional_data.recipientOrgInfos.0.orgIDs"),
    ("Recipient Org: Latest Income (additional data)", "result.additional_data.recipientOrgInfos.0.latestIncome"),
    ("Recipient Org: Latest Income Date (additional data)", "result.additional_data.recipientOrgInfos.0.latestIncomeDate"),
    ("Recipient Org: Org Type (additional data)", "result.additional_data.recipientOrgInfos.0.organisationTypePrimary"),
    ("Recipient Org: Registered Postcode (additional data)", "result.additional_data.recipientOrgInfos.0.postalCode"),
    ("Recipient Org: Data Source (additional data)", "result.additional_data.recipientOrgInfos.0.source"),
    ("Recipient Org: Canonical Org ID (additional data)", "result.additional_data.GNCanonicalRecipientOrgId"),
    ("Recipient Org: Canonical Name (additional data)", "result.additional_data.GNCanonicalRecipientOrgName"),

    # These two always need to be on the end
    ("#comment License (see note)", "dataset.license"),
    ("#comment See http://grantnav.threesixtygiving.org/datasets/ for further license information.", ""),
])

grant_csv_titles = list(grants_csv.keys())
grant_csv_paths = list(grants_csv.values())

org_csv_titles = [
    "Grants",
    "Total",
    "Average",
    "Largest",
    "Smallest"
]

recipient_csv_titles = ["Recipient Name", "Recipient ID"] + org_csv_titles
funder_csv_titles = ["Funder Name", "Funder ID"] + org_csv_titles

org_csv_paths = [
    "org_name",
    "org_id",
    "count",
    "sum",
    "avg",
    "max",
    "min"
]


def grants_csv_to_dictionary():
    """ takes grants_csv and turns it into a dictionary of parent/child
    fields e.g.

    res["Planned Dates"] = [
     {'title': 'Start Date', 'path': 'result.plannedDates.0.startDateDateOnly'},
     {'title': 'End Date', 'path': 'result.plannedDates.0.endDateDateOnly'},
     {'title': 'Duration (months)', 'path': 'result.plannedDates.0.duration'}
    ]
    """
    res = {}

    for title, path in grants_csv.items():
        parsed = title.split(":")
        # initialise array if needed
        if not res.get(parsed[0]):
            res[parsed[0]] = []

        if len(parsed) > 1:
            display_title = ": ".join(parsed[1:])
        else:
            display_title = title

        res[parsed[0]].append({"title": display_title, "path":
                               path, "column_title": title})

    return res


grants_csv_dict = grants_csv_to_dictionary()
