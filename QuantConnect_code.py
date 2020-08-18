# NOTICE: this code is meant to run on QuantConnect.com and attached to a trading broker
# it's here only for show and will not function properly if run in a normal IDE

# Created by Seth Michel, Nathan Wisner, and Brandon Davison

class CustomFeeModel(FeeModel):
        def __init__(self, algorithm):
            self.algorithm = algorithm
    
        def GetOrderFee(self, parameters):
            # custom fee math
            fee = 0
            self.algorithm.Log("CustomFeeModel: " + str(fee))
            return OrderFee(CashAmount(fee, "USD"))


class Marvin(QCAlgorithm):

    def Initialize(self, maximumDrawdownPercent=0.05):
        '''Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.'''

        self.SetStartDate(2018,3,24)   # Set Start Date
        self.SetEndDate(2020,4,7)      # Set End Date
        self.SetCash(25000)            # Set Strategy Cash
        self.testingStocks = ['TSLA', 'F', 'MSFT', 'QQQ', 'DGAZ', 'APPL', 'SBUX', 'DIS']

        # what resolution should the data *added* to the universe be?
        self.__submittedMarketOnCloseToday = False
        self.UniverseSettings.Resolution = Resolution.Minute
        self.security = self.AddEquity('MSFT', Resolution.Minute)
        self.security.SetFeeModel(CustomFeeModel(self))
        self._changes = None
        self.file= None
        
        if self.file is None:
            self.DownloadData()

        # this add universe method accepts a single parameter that is a function that
        # accepts an IEnumerable<CoarseFundamental> and returns IEnumerable<Symbol>
        self.AddTestingStocks()
        
        self.rsiList = self.GetTestingRSI()
        self.maximumDrawdownPercent = -abs(maximumDrawdownPercent)
        
        self.Schedule.On(self.DateRules.EveryDay(), \
        self.TimeRules.At(9, 51), \
        self.BuyPenny)
        
        #At 3:50, 10min before close, sell everything
        self.Schedule.On(self.DateRules.EveryDay(),\
        self.TimeRules.At(15, 50), \
        self.sellPortfolio)

    # sort the data by daily dollar volume and take the top 'NumberOfSymbols'
    def PennyStockSelection(self, coarse):
        
        # sort descending by daily dollar volume
        filtered = sorted(coarse, key=lambda x: x.Price, reverse=True)
        
        filtered = [x.Symbol for x in coarse if x.Price > 0.01 and x.Price < 3]
        
        for item in filtered:
            self.AddEquity(item, Resolution.Minute)
            
        # return the symbol objects of the top entries from our sorted collection
        return filtered
        
    def AddTestingStocks(self):
        for item in self.file:
            self.AddEquity(item, Resolution.Minute)
            
    def GetTestingRSI(self):
        testList = []
        for item in self.file:
            testList.append(self.RSI(item, 14, MovingAverageType.Simple, Resolution.Daily))
        return testList

    def OnData(self, data):
        return

    def BuyPenny(self):
        portfolio = self.Portfolio.Cash

        if portfolio > 900:
            for i in range(len(self.rsiList)):
                portfolio = self.Portfolio.Cash
                
                if portfolio < 900:
                    return
                
                rsi = self.rsiList[i]
                
                if not rsi.IsReady:
                    return
                
                bought = self.Portfolio[self.file[i]].Quantity

                self.Debug(rsi)
                if rsi.Current.Value > 90 and bought == 0:
                    self.SetHoldings(self.file[i], -0.3)
                    
                if rsi.Current.Value < 30 and bought > 0:
                    self.Liquidate(self.file[i])

    # this event fires whenever we have changes to our universe
    def OnSecuritiesChanged(self, changes):
        self._changes = changes
        
    def sellPortfolio(self):
        self.Liquidate()
        
    def DownloadData(self):
        self.file = self.Download("")   # self.Download() arg redacted, you gotta fill it out yourself
        self.file = self.file.split(',\r\n')
                
    def ManageRisk(self, algorithm, targets):
        '''Manages the algorithm's risk at each time step
        Args:
            algorithm: The algorithm instance
            targets: The current portfolio targets to be assessed for risk'''
        targets = []
        for kvp in algorithm.Securities:
            security = kvp.Value

            if not security.Invested:
                continue

            pnl = security.Holdings.UnrealizedProfitPercent
            if pnl < self.maximumDrawdownPercent:
                # liquidate
                targets.append(PortfolioTarget(security.Symbol, 0))

        return targets