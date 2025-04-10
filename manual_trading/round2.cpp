#include <iostream>
#include <vector>
#include <random>
#include <cmath>

using namespace std;

class Container {
	int _multi;
	int _inhab;
	int _people_choice = 0;
public:
	Container (int m, int i) : _multi(m), _inhab(i) {};
	int getValue(){
		return _multi * 10000 / (_inhab + _people_choice);
	}
	void updatePeopleChoice(int pc) {
		_people_choice = pc;
	};
	int getPeopleChoice() const{
		return _people_choice;
	}
	string getInfo(){
		return "Multipler: " + to_string(_multi) + " | " + "Inhabitants: " + to_string(_inhab) + " | " + "People Choice: " + to_string(_people_choice) + " | " + "Value: " + to_string(this->getValue());
	}
};

// Function to calculate the CDF of the normal distribution at x
double normal_cdf(double x, double mean, double stddev) {
    return 0.5 * (1 + erf((x - mean) / (stddev * sqrt(2))));
}

// Function to calculate the discrete probability for x
double discrete_normal_probability(int x) {
	double mean = 0.0;
	double stddev = 2.0;                                   // --------  PREDICTION_MACRO
    double cdf_x = normal_cdf(x, mean, stddev);
    double cdf_x1 = normal_cdf(x + 1, mean, stddev);

    return round((cdf_x1 - cdf_x)*100)*2;
}

class Layer {
	vector<Container> _containers;
	int _depth = 0;
	
	void sort_containers(){
		sort(_containers.begin(), _containers.end(), [](Container &c1, Container &c2){ return c1.getValue() > c2.getValue(); });
	}
public:
	Layer (vector<Container>& cont) {
		_containers = cont;
		sort_containers();
	}

	vector <Container> getSelected () const {
		return vector<Container>(_containers.begin(), _containers.begin() + min<size_t>(_containers.size(), 2));
	}

	void predict_forward() {
		for (int i = 0; i < _containers.size(); ++i){
			pair<double,double> WEIGHT_MACRO = (_depth == 0) ? make_pair(1.,0.) : make_pair(1.0/((_depth+6)*2),1.0- 1.0/((_depth+6)*2));
			//cout << temp << endl;
			_containers[i].updatePeopleChoice(round(discrete_normal_probability(i)*WEIGHT_MACRO.first + _containers[i].getPeopleChoice()*WEIGHT_MACRO.second));
		}
		sort_containers();
		_depth++;
		this->print_outcome();
	}

	void print_outcome(){
		cout << "Layer " + to_string(_depth) + " output value *******************" << endl;
		for (auto val: _containers){
			cout << val.getInfo() << endl;
		}
		cout << "****************************************" << endl;
		cout << endl;
	}
};


int main(){
	vector<Container> containers = {Container(10,1), Container(80,6), Container(37,3), Container(17,1), Container(31,2), 
		Container(90,10), Container(50,4), Container(20,2), Container(73,4), Container(89,8)};

	Layer layer(containers);

	layer.print_outcome();

	// add what other team's action constraint
	for (int i =0; i< 2; i++)
		layer.predict_forward();

	//layer.print_outcome();
}