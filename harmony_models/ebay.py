import typing


class ParseResult:
    def __init__(
            self,
            trimmed_price_list: typing.List[float],
            trim_percentage: float,
            trim_count: int,
            original_prices_count: int
    ):
        """
        Create a ParseResult (the result of parsing an eBay search results page).
        :param trimmed_price_list: The trimmed list of prices.
        :param trim_percentage: The percentage of results that were trimmed from the original price list.
        :param trim_count: The number of results that were trimmed from each end of the original price list.
        :param original_prices_count: The number of prices before trimming.
        """
        self.trimmed_price_list = trimmed_price_list
        self.trim_percentage = trim_percentage
        self.trim_count = trim_count
        self.original_prices_count = original_prices_count


class ResultStatistics:
    def __init__(
            self,
            trimmed_mean: float,
            median: float,
            mode: float,
            min_price: float,
            max_price: float
    ):
        """
        Create a set of statistics based on a ParseResult.
        :param trimmed_mean: The mean of the trimmed price list.
        :param median: The median of the trimmed price list.
        :param mode: The mode of the trimmed price list.
        :param min_price: The minimum price of the trimmed price list.
        :param max_price: The maximum price of the trimmed price list.
        """
        self.trimmed_mean = trimmed_mean
        self.median = median
        self.mode = mode
        self.min_price = min_price
        self.max_price = max_price
