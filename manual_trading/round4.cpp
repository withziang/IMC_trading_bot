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
	int getMulti(){
		return _multi;
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
double discrete_normal_probability(int x, double stddev = 6.0) {
	double mean = 0.0;
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
		consider_only_multi();
		bias_from_round2();
		sort_containers();
		_depth++;
		print_outcome();
	}

	void consider_only_multi(){
		sort(_containers.begin(), _containers.end(), [](Container &c1, Container &c2){ return c1.getMulti() > c2.getMulti(); });
		pair<double,double> WEIGHT_MACRO = {0.4, 0.6};

		for (int i = 0; i < _containers.size(); ++i){
			_containers[i].updatePeopleChoice(round(discrete_normal_probability(i, 4.0)*WEIGHT_MACRO.first + _containers[i].getPeopleChoice()*WEIGHT_MACRO.second));
		}
	}

	void bias_from_round2(){
		sort(_containers.begin(), _containers.end(), [](Container &c1, Container &c2){ return c1.getMulti() < c2.getMulti(); });
		pair<double,double> WEIGHT_MACRO = {0.1, 0.9};

		for (int i = 0; i < _containers.size(); ++i){
			_containers[i].updatePeopleChoice(round(discrete_normal_probability(i, 2.0)*WEIGHT_MACRO.first + _containers[i].getPeopleChoice()*WEIGHT_MACRO.second));
		}
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
	vector<Container> containers = {
	    // Row A
	    Container(80, 6), Container(50, 4), Container(83, 7), Container(31, 2), Container(60, 4),
	    
	    // Row B
	    Container(89, 8), Container(10, 1), Container(37, 3), Container(78, 4), Container(98, 10),
	    
	    // Row C
	    Container(17, 1), Container(40, 3), Container(73, 4), Container(100, 15), Container(20, 2),
	    
	    // Row D
	    Container(41, 3), Container(79, 5), Container(23, 2), Container(47, 3), Container(30, 2)
	
	};


	Layer layer(containers);

	layer.print_outcome();

	// add what other team's action constraint

	layer.predict_forward();
	layer.predict_forward();

	//layer.print_outcome();
}