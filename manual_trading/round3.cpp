#include <iostream>
#include <cmath>

using namespace std;


// two bids: lowest bid, second bid > the average
// <, they will take the first one 100%, > will take the first one if it is higher > the average second bids

// 40+70/110, 55 => 265 

// Function to calculate the CDF of the normal distribution at x
double normal_cdf(double x) { // return p(potential mean < x)
	double mean = 285.0;
	double stddev = 2.0; 
    return 0.5 * (1 + erf((x - mean) / (stddev * sqrt(2))));
}


double get_probability(int x){
	return (1-normal_cdf(x))*pow(35,3)*(x-250)/(pow(320-x,2)*70) + normal_cdf(x)*(320-x)*(x-250)/70;
}



int main(){
	pair<double,int> ans = {-1.0,-1};
	for (int i = 250; i<320;i++){
		auto p = get_probability(i);
		ans = max(make_pair(p, i), ans);
		cout << p << " ";
	}
	cout << endl;
	cout << ans.first << " " << ans.second;
}