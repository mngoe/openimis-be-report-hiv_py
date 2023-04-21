from tokenize import String
from django.db import models
from django.db.models import Q
from core import models as core_models
from medical.models import Item, Service
from report.services import run_stored_proc_report
from claim.models import Claim, ClaimService, ClaimItem, ClaimServiceService, ClaimServiceItem
from location.models import Location, HealthFacility
from policy.models import Policy
from insuree.models import Insuree
from collections import defaultdict
from django.db.models import Count
from django.db.models import F
from insuree.models import Insuree
from insuree.models import InsureePolicy
import json
import datetime
from program import models as program_models

def invoice_hiv_query(user, **kwargs):
    print("Me voici alors")
    date_from = kwargs.get("date_from")
    date_to = kwargs.get("date_to")
    location0 = kwargs.get("location0")
    location1 = kwargs.get("location1")
    location2 = kwargs.get("location2")
    hflocation = kwargs.get("hflocation")
    
    format = "%Y-%m-%d"

    date_from_object = datetime.datetime.strptime(date_from, format)
    date_from_str = date_from_object.strftime("%d/%m/%Y")

    date_to_object = datetime.datetime.strptime(date_to, format)
    date_to_str = date_to_object.strftime("%d/%m/%Y")

    dictGeo = {}
    dictBase = {
        "dateFrom": date_from_str,
        "dateTo": date_to_str
    }
    # If there is HealthFacility defined in the form
    if hflocation and hflocation!="0" :
        hflocationObj = HealthFacility.objects.filter(
            code=hflocation,
            validity_to__isnull=True
            ).first()
        dictBase["fosa"] = hflocationObj.name
        dictGeo['health_facility'] = hflocationObj.id
    
    # Get all 5 Programs
    today = datetime.datetime.now()
    programs = program_models.Program.objects.filter(
        validityDateFrom__lte=today).filter(
        Q(validityDateTo__isnull=True) | Q(validityDateTo__gte=today)
        ).order_by('-idProgram')[:5]
    
    program_ids = []
    for prg in programs:
        program_ids.append(prg)
    number = len(program_ids)
    # Complete to 5 elements if the result is less than 5
    while number < 5:
        program_ids.append(0)
        number += 1

    invoiceElemtTotal_MontantRecueTotal = 0
    invoiceElemtTotal_MtnValideTotal = 0
    i = 1
    for program in program_ids:
        if i == 1:
            dictBase.update({
                "prestationForfaitaire" : [],
                "prestationPlafonnees" : [],
                "prestationsNonMedicales" : [],
                "invoiceElemtTotal": [],
                "Program1": program.nameProgram if program != 0 else " "
            })
        else:
            dictBase.update({
                "prestationForfaitaireProgram"+str(i): [],
                "prestationPlafonneesProgram"+str(i): [],
                "prestationsNonMedicalesProgram"+str(i) : [],
                "invoiceElemtTotalProgram"+str(i): [],
                "Program"+str(i): program.nameProgram if program != 0 else " "
            })
        ## Get All claim corresponding to parameter sent
        value = program.idProgram if program != 0 else 0
        claimList = Claim.objects.exclude(
            status=1
        ).filter(
            date_from__gte=date_from,
            date_from__lte=date_to,
            validity_to__isnull=True,
            program=value,
            **dictGeo
        )

        invoiceElemtList = defaultdict(dict)
        invoiceElemtTotal = defaultdict(int)
        invoiceElemtListP = []
        invoiceElemtListF = []
        invoiceElemtListS = []


        for cclaim in claimList:
            #First we calculate on each Service inside a
            claimService = ClaimService.objects.filter(
                claim = cclaim,
                status=1
            )
            for claimServiceElmt in claimService:
                invoiceElemtTotal[claimServiceElmt.service.packagetype+"QtyValuatedV"] = 0
                invoiceElemtTotal[claimServiceElmt.service.packagetype+"MtnValideV"] = 0
                if claimServiceElmt.service.id not in invoiceElemtList[claimServiceElmt.service.packagetype]:
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id] = defaultdict(dict)
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"] = defaultdict(int)
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecue"] = 0

                ## Define global information of each Line
                invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["name"] = claimServiceElmt.service.name
                invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["code"] = claimServiceElmt.service.code
                if claimServiceElmt.service.packagetype == "F":
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["tarif"] = claimServiceElmt.service.price
                else:
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["tarif"] = claimServiceElmt.price_asked
                ## Status Valuated of Claim          
                if cclaim.status==16:
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"]['valuated'] += int(claimServiceElmt.qty_provided)
                    if claimServiceElmt.price_valuated == None :
                        claimServiceElmt.price_valuated = 0
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"]['sum'] += int(claimServiceElmt.qty_provided * claimServiceElmt.price_valuated)
                    invoiceElemtTotal[claimServiceElmt.service.packagetype+"QtyValuatedV"] += int(invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"]['valuated'])
                    invoiceElemtTotal[claimServiceElmt.service.packagetype+"MtnValideV"] += int(invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"]['sum'])

                invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"]['all'] += claimServiceElmt.qty_provided            
                ## Specific Rules for Montant Recue (for different type of package)
                if claimServiceElmt.service.packagetype == "S":
                    invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecue"] += invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"]['all'] * invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["tarif"]
                else :
                    if claimServiceElmt.service.manualPrice == True :
                        invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecue"] += invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["qty"]['all'] * claimServiceElmt.service.price
                    else : 
                        claimSs = ClaimServiceService.objects.filter(
                            claimlinkedService = claimServiceElmt
                        )
                        tarifLocal = 0
                        for claimSsElement in claimSs:
                            tarifLocal += claimSsElement.qty_displayed * claimSsElement.price_asked
                        #    print(tarifLocal)
                        claimSi = ClaimServiceItem.objects.filter(
                            claimlinkedItem = claimServiceElmt
                        )
                        for claimSiElement in claimSi:
                            tarifLocal += claimSiElement.qty_displayed * claimSiElement.price_asked
                            #print(tarifLocal)
                        #print(type(tarifLocal))
                        invoiceElemtList[claimServiceElmt.service.packagetype][claimServiceElmt.service.id]["MontantRecue"] += tarifLocal
                
                
                if claimServiceElmt.service.packagetype not in invoiceElemtTotal :
                    invoiceElemtTotal[claimServiceElmt.service.packagetype] = defaultdict(int)

                ### Sum of all line at footer of table 
                invoiceElemtTotal[claimServiceElmt.service.packagetype+"QtyTotalV"] += int(claimServiceElmt.qty_provided)
                MtnNotValideV = 0
                if int(invoiceElemtTotal[claimServiceElmt.service.packagetype+"MontantRecueTotalV"] - invoiceElemtTotal[claimServiceElmt.service.packagetype+"MtnValideV"]) > 0:
                    MtnNotValideV = int(invoiceElemtTotal[claimServiceElmt.service.packagetype+"MontantRecueTotalV"] - invoiceElemtTotal[claimServiceElmt.service.packagetype+"MtnValideV"])
                invoiceElemtTotal[claimServiceElmt.service.packagetype+"MtnNotValideV"] = MtnNotValideV
                invoiceElemtTotal["QtyTotalV"] += int(claimServiceElmt.qty_provided)

            #Then we calculate on each Item inside a claim
            # claimItem = ClaimItem.objects.filter(
            #     claim = cclaim,
            #     status=1
            # )
            # for claimItemElmt in claimItem:
            #     if claimItemElmt.service.id not in invoiceElemtList[claimItemElmt.service.packagetype]:
            #         invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id] = defaultdict(int)

            #     if cclaim.status == "16":
            #         invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["qty"]['valuated'] += claimItemElmt.qty_provided

            #     invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["name"] = claimItemElmt.service.name
            #     invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["code"] = claimItemElmt.service.code
            #     invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["tarif"] = claimItemElmt.price_asked
            #     invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["qty"]["all"] += claimItemElmt.qty_provided
            #     invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["MontantRecue"] += invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["qty"]['all'] * invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["tarif"]            
                
            #     if claimServiceElmt.service.packagetype not in invoiceElemtTotal :
            #         invoiceElemtTotal[claimServiceElmt.service.packagetype] = defaultdict(int)

            #     invoiceElemtTotal[claimItemElmt.service.packagetype+"QtyTotalV"] += claimItemElmt.qty_provided
            #     invoiceElemtTotal[claimItemElmt.service.packagetype+"QtyValuatedV"] += int(invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["qty"]['valuated'])
            #     invoiceElemtTotal[claimItemElmt.service.packagetype+"MtnValideV"] += invoiceElemtList[claimItemElmt.service.packagetype][claimItemElmt.service.id]["qty"]['sum']
            #     MtnNotValideV = 0
            #     if invoiceElemtTotal[claimItemElmt.service.packagetype+"MontantRecueTotal"] - invoiceElemtTotal[claimItemElmt.service.packagetype+"MtnValide"] > 0:
            #         MtnNotValideV = invoiceElemtTotal[claimItemElmt.service.packagetype+"MontantRecueTotal"] - invoiceElemtTotal[claimItemElmt.service.packagetype+"MtnValide"]
            #     invoiceElemtTotal[claimItemElmt.service.packagetype+"MtnNotValideV"] = MtnNotValideV
            #     invoiceElemtTotal["QtyTotalV"] += claimItemElmt.qty_provided
        
        invoiceElemtTotal["PQtyValuatedV"]=0
        invoiceElemtTotal["PMontantRecueTotalV"] = 0
        invoiceElemtTotal["PMtnNotValideV"] = 0
        invoiceElemtTotal["PMtnValideV"] = 0
        invoiceElemtTotal["FMontantRecueTotalV"] = 0
        invoiceElemtTotal["FQtyValuatedV"] = 0
        invoiceElemtTotal["FMtnNotValideV"] = 0
        invoiceElemtTotal["FMtnValideV"] = 0 
        invoiceElemtTotal["SQtyValuatedV"] = 0
        invoiceElemtTotal["SMontantRecueTotalV"] = 0
        invoiceElemtTotal["SMtnNotValideV"] = 0
        invoiceElemtTotal["SMtnValideV"] = 0
        
        # print ("{:<5} {:<5} {:<40} {:<10} {:<10} {:<10} {:<10} {:<20}".format('type','id','name','Code','tarif','qty', 'Montant Recus','Qty Validated'))
        # print("invoiceElemtList ", invoiceElemtList)
        for typeList,v in invoiceElemtList.items():
            for id in v:
                montantNonValide = 0
                # Correction des chiffres negatif : -- Si un montant est negatif ca veut dire que le montant valuated est superieur a la somme des sous-services / services
                # if v[id]['MontantRecue'] - v[id]['qty']['sum'] > 0 :
                montantNonValide = v[id]['MontantRecue'] - v[id]['qty']['sum']
                if typeList=="P":
                    invoiceElemtListP.append(dict(
                        name=v[id]['name'],
                        code=v[id]['code'],
                        tarif=str("{:,.0f}".format(v[id]['tarif'])),
                        nbrFacture = str(v[id]['qty']['all']),
                        mtnFactureRecues= str("{:,.0f}".format(v[id]['MontantRecue'])),
                        nbFactureValides= str(v[id]['qty']['valuated']),
                        montantNonValide = str("{:,.0f}".format(montantNonValide)),
                        montantValide =  str("{:,.0f}".format(v[id]['qty']['sum']))
                        ))
                    
                    invoiceElemtTotal["PMontantRecueTotalV"] += v[id]['MontantRecue']
                    invoiceElemtTotal["PQtyValuatedV"] += v[id]['qty']['valuated']
                    PMtnNotValideV = 0;
                    if v[id]['MontantRecue'] - v[id]['qty']['sum'] > 0:
                        PMtnNotValideV = v[id]['MontantRecue'] - v[id]['qty']['sum']
                    invoiceElemtTotal["PMtnNotValideV"] += PMtnNotValideV
                    invoiceElemtTotal["PMtnValideV"] += v[id]['qty']['sum']

                if typeList=="F":
                    invoiceElemtListF.append(dict(
                        name=v[id]['name'],
                        code=v[id]['code'],
                        tarif=str("{:,.0f}".format(v[id]['tarif'])),
                        nbrFacture = str(v[id]['qty']['all']),
                        mtnFactureRecues= str("{:,.0f}".format(v[id]['MontantRecue'])),
                        nbFactureValides= str(v[id]['qty']['valuated']),
                        montantNonValide = str("{:,.0f}".format(montantNonValide)),
                        montantValide =  str("{:,.0f}".format(v[id]['qty']['sum']))                    
                        ))
                    invoiceElemtTotal["FMontantRecueTotalV"] += v[id]['MontantRecue']
                    invoiceElemtTotal["FQtyValuatedV"] += v[id]['qty']['valuated']
                    FMtnNotValideV = 0;
                    if v[id]['MontantRecue'] - v[id]['qty']['sum'] > 0:
                        FMtnNotValideV = v[id]['MontantRecue'] - v[id]['qty']['sum']
                    invoiceElemtTotal["FMtnNotValideV"] += FMtnNotValideV
                    invoiceElemtTotal["FMtnValideV"] += v[id]['qty']['sum']

                
                if typeList=="S":
                    invoiceElemtListS.append(dict(
                        name=v[id]['name'],
                        code=v[id]['code'],
                        tarif=str("{:,.0f}".format(v[id]['tarif'])),
                        nbrFacture = str(v[id]['qty']['all']),
                        mtnFactureRecues= str("{:,.0f}".format(v[id]['MontantRecue'])),
                        nbFactureValides= str(v[id]['qty']['valuated']),
                        montantNonValide = str("{:,.0f}".format(v[id]['MontantRecue'] - v[id]['qty']['sum'])),
                        montantValide =  str("{:,.0f}".format(v[id]['qty']['sum']))
                        ))
                    invoiceElemtTotal["SMontantRecueTotalV"] += v[id]['MontantRecue']
                    invoiceElemtTotal["SQtyValuatedV"] += v[id]['qty']['valuated']
                    invoiceElemtTotal["SMtnNotValideV"] += v[id]['MontantRecue'] - v[id]['qty']['sum']
                    invoiceElemtTotal["SMtnValideV"] += v[id]['qty']['sum']

                # print("{:<5} {:<5} {:<40} {:<10} {:<10} {:<10} {:<10} {:<10}".format(
                    # typeList, id, v[id]['name'], v[id]['code'], v[id]['tarif'],v[id]['qty']['all'], v[id]['MontantRecue'],v[id]['qty']['valuated']
                    # ))

        ## Calcaulating of each invoiceElemtTotal
        invoiceElemtTotal["NbFactureValideTotal"] = invoiceElemtTotal["FQtyValuatedV"] + invoiceElemtTotal["SQtyValuatedV"] + invoiceElemtTotal["PQtyValuatedV"]
        invoiceElemtTotal["NbFactureValideTotal"] = "{:,.0f}".format(invoiceElemtTotal["NbFactureValideTotal"])
        invoiceElemtTotal["FQtyValuated"] = "{:,.0f}".format(invoiceElemtTotal["FQtyValuatedV"])
        invoiceElemtTotal["SQtyValuated"] = "{:,.0f}".format(invoiceElemtTotal["SQtyValuatedV"])
        invoiceElemtTotal["PQtyValuated"] = "{:,.0f}".format(invoiceElemtTotal["PQtyValuatedV"])
        invoiceElemtTotal["FQtyTotal"] = "{:,.0f}".format(invoiceElemtTotal["FQtyTotalV"])
        invoiceElemtTotal["SQtyTotal"] = "{:,.0f}".format(invoiceElemtTotal["SQtyTotalV"])
        invoiceElemtTotal["PQtyTotal"] = "{:,.0f}".format(invoiceElemtTotal["PQtyTotalV"])

        invoiceElemtTotal["MtnValideTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMtnValideV"]+invoiceElemtTotal["SMtnValideV"]+invoiceElemtTotal["PMtnValideV"])
        invoiceElemtTotal_MtnValideTotal += invoiceElemtTotal["FMtnValideV"]+invoiceElemtTotal["SMtnValideV"]+invoiceElemtTotal["PMtnValideV"]
        invoiceElemtTotal["FMtnValide"] = "{:,.0f}".format(invoiceElemtTotal["FMtnValideV"])
        invoiceElemtTotal["SMtnValide"] = "{:,.0f}".format(invoiceElemtTotal["SMtnValideV"])
        invoiceElemtTotal["PMtnValide"] = "{:,.0f}".format(invoiceElemtTotal["PMtnValideV"])
        invoiceElemtTotal["MtnNonValideTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMtnNotValideV"]+invoiceElemtTotal["SMtnNotValideV"]+invoiceElemtTotal["PMtnNotValideV"])
        invoiceElemtTotal["FMtnNotValide"] = "{:,.0f}".format(invoiceElemtTotal["FMtnNotValideV"])
        invoiceElemtTotal["SMtnNotValide"] = "{:,.0f}".format(invoiceElemtTotal["SMtnNotValideV"])
        invoiceElemtTotal["PMtnNotValide"] = "{:,.0f}".format(invoiceElemtTotal["PMtnNotValideV"])

        invoiceElemtTotal["MontantRecueTotal"] =  "{:,.0f}".format(invoiceElemtTotal["PMontantRecueTotalV"]+invoiceElemtTotal["FMontantRecueTotalV"]+invoiceElemtTotal["SMontantRecueTotalV"])
        invoiceElemtTotal_MontantRecueTotal += invoiceElemtTotal["PMontantRecueTotalV"]+invoiceElemtTotal["FMontantRecueTotalV"]+invoiceElemtTotal["SMontantRecueTotalV"]
        print("invoiceE_____RecueTotal ", invoiceElemtTotal_MontantRecueTotal)
        print("invoiceElemtTotal_MtnValideTotal ", invoiceElemtTotal_MtnValideTotal)
        invoiceElemtTotal["PMontantRecueTotal"] = "{:,.0f}".format(invoiceElemtTotal["PMontantRecueTotalV"])
        invoiceElemtTotal["SMontantRecueTotal"] = "{:,.0f}".format(invoiceElemtTotal["SMontantRecueTotalV"])
        invoiceElemtTotal["FMontantRecueTotal"] = "{:,.0f}".format(invoiceElemtTotal["FMontantRecueTotalV"])

        invoiceElemtTotal["QtyTotal"] = "{:,.0f}".format(invoiceElemtTotal["QtyTotalV"])    

        if i == 1:
            dictBase["prestationForfaitaire"] = invoiceElemtListP
            dictBase["prestationPlafonnees"] = invoiceElemtListF
            dictBase["prestationsNonMedicales"] = invoiceElemtListS
            dictBase["invoiceElemtTotal"] = invoiceElemtTotal
            print("Premier dict base est")
            print(dictBase["invoiceElemtTotal"])
        else:
            dictBase["prestationForfaitaireProgram"+str(i)] = invoiceElemtListP
            dictBase["prestationPlafonneesProgram"+str(i)] = invoiceElemtListF
            dictBase["prestationsNonMedicalesProgram"+str(i)] = invoiceElemtListS
            dictBase["invoiceElemtTotalProgram"+str(i)] = invoiceElemtTotal
            print(dictBase["invoiceElemtTotalProgram"+str(i)])
        i += 1
    print("invoiceElemtTotal_MontantRecueTotal is ", invoiceElemtTotal_MontantRecueTotal)
    print("invoiceElemtTotal_MtnValideTotal is ", invoiceElemtTotal_MtnValideTotal)
    # dictBase["invoiceElemtTotal"]["MontantRecueTotal"] =  "{:,.0f}".format(invoiceElemtTotal_MontantRecueTotal)
    # dictBase["invoiceElemtTotal"]["MtnValideTotal"] =  "{:,.0f}".format(invoiceElemtTotal_MtnValideTotal)
    dictBase["MontnRecueTotal"] =  "{:,.0f}".format(invoiceElemtTotal_MontantRecueTotal)
    dictBase["MtnValideTotal"] =  "{:,.0f}".format(invoiceElemtTotal_MtnValideTotal)
    
    print(dictBase)

    if location0:
        location0_str = Location.objects.filter(
            code=location0,
            validity_to__isnull=True
            ).first().name
        dictBase["region"] = location0_str

    if location1:
        location1_str = Location.objects.filter(
            code=location1,
            validity_to__isnull=True
            ).first().name
        dictBase["district"] =location1_str
    
    if location2:
        location2_str = Location.objects.filter(
            code=location2,
            validity_to__isnull=True
            ).first().name
        dictBase["area"] = location2_str
    
    return dictBase
