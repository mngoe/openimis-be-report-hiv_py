from report.services import run_stored_proc_report
from claim.models import ClaimService, Claim, ClaimItem
from location.models import Location, HealthFacility
import datetime
import time

val_de_zero = [
    'million', 'milliard', 'billion',
    'quadrillion', 'quintillion', 'sextillion',
    'septillion', 'octillion', 'nonillion',
    'décillion', 'undecillion', 'duodecillion',
    'tredecillion', 'quattuordecillion', 'sexdecillion',
    'septendecillion', 'octodecillion', 'icosillion', 'vigintillion'
]

to_19_fr = (
    'zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six',
    'sept', 'huit', 'neuf', 'dix', 'onze', 'douze', 'treize',
    'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf'
)

tens_fr  = (
    'vingt', 'trente', 'quarante', 'cinquante', 'soixante', 'soixante',
    'quatre-vingts', 'quatre-vingt'
)

denom_fr = (
    '', 'mille', 'million', 'milliard', 'billion', 'quadrillion',
    'quintillion', 'sextillion', 'septillion', 'octillion', 'nonillion',
    'décillion', 'undecillion', 'duodecillion', 'tredecillion',
    'quattuordecillion', 'sexdecillion', 'septendecillion',
    'octodecillion', 'icosillion', 'vigintillion'
)

denoms_fr = (
    '', 'mille', 'millions', 'milliards', 'billions', 'quadrillions',
    'quintillions', 'sextillions', 'septillions', 'octillions', 'nonillions',
    'décillions', 'undecillions', 'duodecillions', 'tredecillions',
    'quattuordecillions', 'sexdecillions', 'septendecillions',
    'octodecillions', 'icosillions', 'vigintillions'
)

def _convert_nnn_fr(val):
    """
    \detail         convert a value < 1000 to french
        special cased because it is the level that kicks 
        off the < 100 special case.  The rest are
        more general.  This also allows you to
        get strings in the form of 'forty-five hundred' if called directly.
    \param  val     value(int or float) to convert
    \return         a string value
    """
    word = ''
    (mod, rem) = (val % 100, val // 100)
    if rem > 0:
        if (rem>1 and rem <10 and mod <= 0): 
             word = to_19_fr[rem] + ' cents'
        else: 
             word = to_19_fr[rem] + ' cent'
             
        if mod > 0:
            word += ' '
    if mod > 0:
        word += _convert_nn_fr(mod)
    return word

def _convert_nn_fr(val):
    """
    \brief       convert a value < 100 to French
    \param  val  value to convert 
    """
    if val < 20:
        return to_19_fr[val]
    for (dcap, dval) in ((k, 20 + (10 * v)) for (v, k) in enumerate(tens_fr)):
        if dval + 10 > val:
            if dval in (70,90):
                return dcap + '-' + to_19_fr[val % 10 + 10]
            if val % 10:
                return dcap + '-' + to_19_fr[val % 10]
            return dcap

def french_number(val):
    
    """
    \brief       Convert a numeric value to a french string
        Dispatch diffent kinds of number depending
        on their value (<100 or < 1000)
        Then create a for loop to rewrite cutted number.
    \param  val  value(int or float) to convert
    \return      a string value
    """
    
    if val < 100:
        return _convert_nn_fr(val)
    if val < 1000:
         return _convert_nnn_fr(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom_fr))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            
            pref_final = _convert_nnn_fr(l)
            pref = pref_final.split(' ')
            if(pref[len(pref)-1] == ' cent'):
                pref[len(pref)-1] = " cents"
                pref_final = " ".join(x for x in pref)
            if l>1:    
                ret = pref_final + ' ' + denoms_fr[didx]
            else:
                ret = pref_final + ' ' + denom_fr[didx]
            if r > 0:
                ret = ret + ' ' + french_number(r)
            return ret

def amount_to_text_fr(number, currency):
    """
    \brief              convert amount value to french string
        reuse the french_number function
        to write the correct number
        in french, then add the specific cents for number < 0
        and add the currency to the string
    \param  number      the number to convert
    \param  currency    string value of the currency
    \return             the string amount in french
    """
    try:
        number = int(number)
    except:
        return 'Traduction error'
    number = '%.2f' % number
    units_name = currency
    list = str(number).split('.')
    start_word = french_number(abs(int(list[0])))

    #On enleve le un au debut de la somme écrite en lettre.
    liste = str(start_word).split(' ')
    for i in range(len(liste)):
        item = liste[i]
        tab=liste
        if item =='un':
            if i==0 and len(liste) > 1:
                if liste[i+1] not in val_de_zero:
                    tab[i]=""
            elif i > 0 and len(liste) > 1:
                if i < len(liste)-1:
                    if liste[i+1] not in val_de_zero:
                        if not liste[i-1] in ["cent", "cents"] and not (liste[i+1] in val_de_zero or liste[i+1] in denom_fr or liste[i+1] in denoms_fr):
                            tab[i]=""
            start_word = " ".join(x for x in tab)
    french_number(int(list[1]))
    final_result = start_word +' '+units_name
    return final_result
    
def invoice_hiv_query(user, **kwargs):
    date_from = kwargs.get("date_from")
    date_to = kwargs.get("date_to")
    hflocation = kwargs.get("hflocation")
    
    format = "%Y-%m-%d"
    
    maintenant = time.strftime("%d/%m/%Y %H:%M:%S")
    date_from_object = datetime.datetime.strptime(date_from, format)
    date_from_str = date_from_object.strftime("%d/%m/%Y")

    date_to_object = datetime.datetime.strptime(date_to, format)
    date_to_str = date_to_object.strftime("%d/%m/%Y")

    dictGeo = {}
    dictBase = {}
    total = 0
    element_ids = []
    dictBase["periode"] = str(date_from_str) + " - " + date_to_str
    dictBase["dateFacturation"] = maintenant
    # If there is HealthFacility defined in the form
    if hflocation and hflocation!="0" :
        hflocationObj = HealthFacility.objects.filter(
            code=hflocation,
            validity_to__isnull=True
            ).first()
        dictBase["fosa"] = hflocationObj.name
        dictBase["Phone"] = hflocationObj.phone
        dictGeo['health_facility'] = hflocationObj.id
        level_village = False
        level_district = False
        level_ville = False
        municipality = " "
        district = " "
        village = " "
        if hflocationObj.location.parent:
            level_district = True
            if hflocationObj.location.parent.parent:
                level_ville = True
                if hflocationObj.location.parent.parent.parent:
                    level_village = True
        if level_village:
            village = hflocationObj.location.name
            municipality = hflocationObj.location.parent.name
            district = hflocationObj.location.parent.parent.name
            region = hflocationObj.location.parent.parent.parent.name
        elif level_ville:
            municipality = hflocationObj.location.name
            district = hflocationObj.location.parent.name
            region = hflocationObj.location.parent.parent.name
        elif level_district:
            district = hflocationObj.location.name
            region = hflocationObj.location.parent.name
        else:
            region = hflocationObj.location.name
        print("region ", region)
        print("district ", district)
        print("municipality ", municipality)
        print("village ", village)
    
        dictBase["region"] = region
        dictBase["district"] = district
        dictBase["area"] = municipality
        dictBase["village"] = village

    claimList = Claim.objects.exclude(
        status=1
    ).filter(
        date_from__gte=date_from,
        date_from__lte=date_to,
        validity_to__isnull=True,
        **dictGeo
    )
    data = []

    count = 1
    for cclaim in claimList:
        claimService = ClaimService.objects.filter(
            claim = cclaim,
            status=1
        )
        for claimServiceElmt in claimService:
            if claimServiceElmt.service.id not in element_ids:
                element_ids.append(claimServiceElmt.service.id)
                qty_approved = claimServiceElmt.qty_approved and claimServiceElmt.qty_approved or 0
                qty_provided = 0
                if cclaim.status==16:
                    # Valuated
                    qty_provided = claimServiceElmt.qty_provided and claimServiceElmt.qty_provided or 0
                pu = claimServiceElmt.service.price and claimServiceElmt.service.price or 0
                sous_total = pu * qty_provided
                total += sous_total
                val = {
                    "Numero": str(count),
                    "Nom": claimServiceElmt.service.name,
                    "QteDeclaree": str("{:,.0f}".format(float(qty_approved))),
                    "QteValidee": str("{:,.0f}".format(float(qty_provided))),
                    "PrixUnit": str("{:,.0f}".format(float(pu))),      
                    "Montant": str("{:,.0f}".format(float(int(sous_total))))
                }
                data.append(val)
                count +=1


        # claimItem
        claimItems = ClaimItem.objects.filter(
            claim = cclaim,
            status=1
        )
        for claimItemElmt in claimItems:
            if claimItemElmt.item.id not in element_ids:
                element_ids.append(claimItemElmt.item.id)
                qty_approved = claimItemElmt.qty_approved and claimItemElmt.qty_approved or 0
                qty_provided = 0
                if cclaim.status==16:
                    # Valuated
                    qty_provided = claimItemElmt.qty_provided and claimItemElmt.qty_provided or 0
                pu = claimItemElmt.item.price and claimItemElmt.item.price or 0
                sous_total2 = pu * qty_provided
                total += sous_total2
                val = {
                    "Numero": str(count),
                    "Nom": claimItemElmt.item.name,
                    "QteDeclaree": str("{:,.0f}".format(float(qty_approved))),
                    "QteValidee": str("{:,.0f}".format(float(qty_provided))),
                    "PrixUnit": str("{:,.0f}".format(float(pu))),   
                    "Montant": str("{:,.0f}".format(float(int(sous_total2))))
                }
                data.append(val)
                count +=1
    dictBase["datas"] = data
    dictBase["TOTAL"] = str("{:,.0f}".format(float(int(total)))) + " Francs CFA"
    dictBase["amountLetter"] = amount_to_text_fr(int(total), 'Francs CFA')
    print("dictBase ", dictBase)
    return dictBase
