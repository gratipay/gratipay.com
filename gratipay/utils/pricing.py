from decimal import Decimal as D, ROUND_HALF_EVEN


def suggested_payment(usage):
    pct = D('0.05')
    rounded = nearest_5_calc(usage,pct)

    return rounded


def suggested_payment_low_high(usage):
    # low = 5%, high = 10%
    lowpct = D('0.05')
    low = nearest_5_calc(usage,lowpct)
    highpct = D('0.1')
    high = nearest_5_calc(usage,highpct)

    return low, high

def nearest_5_calc(usage,pct):
    unrounded = usage * pct
    # Round half even to nearest 5 cents
    rounded = (unrounded / D('0.05')).quantize(D('0'), ROUND_HALF_EVEN) * D('0.05') 
    return rounded