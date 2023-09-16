"""
Useful Functions to Extract Aircraft Performance Data

Usage: 
- Import the required function and call it.
"""

from typing import Dict, Union, Any, List


from sqlalchemy.orm import Session

import models


def linear_interpolation(x1, y1, x2, y2, x_target):
    """
    This function performs a 1-dimensional linear interpolation
    """

    # Calculate the slope
    m = (y2 - y1) / (x2 - x1)

    # Use the slope to find the interpolated y-value at x_target
    y_target = y1 + m * (x_target - x1)

    return y_target


def find_nearest_arrays(data: List[Any], target: Union[int, float], attr_name: str):
    """
    This function estracts 2 arrays from the data array and a new target. One array where 
    all the values of the attribute 'attr_name', are immediately less than 'target', and one 
    where they are greater than or equal to 'target'. If 'target' is smaller or higher than 
    all elements in data, the fucntion will return None, in  place of the array with the smaller 
    or higher values, and it will truncate the 'target' to the smallest or highest value, and 
    return it.
    """
    # Perform binary search
    low = 0
    high = len(data) - 1
    while low <= high:
        mid = (low + high) // 2
        if getattr(data[mid], attr_name) < target:
            low = mid + 1
        else:
            high = mid - 1

    # The "low" index points to the first number greater than or equal to x
    # The "high" index points to the last number less than x

    # Check for boundary conditions
    if high == -1:  # target is smaller than all elements in the list
        return (getattr(data[0], attr_name), [
            [row for row in data if getattr(
                row, attr_name) == getattr(data[low], attr_name)]
        ])
    if low == len(data):  # target is greater than or equal to all elements in the list
        return (getattr(data[0], attr_name), [
            [row for row in data if getattr(
                row, attr_name) == getattr(data[high], attr_name)]
        ])

    return (target, [
        [row for row in data if getattr(
            row, attr_name) == getattr(data[high], attr_name)],
        [row for row in data if getattr(
            row, attr_name) == getattr(data[low], attr_name)]
    ])


def recursive_data_interpolation(
    input_names: List[str],
    index: int,
    output_names: List[str],
    interp_data_sets: List[List[Any]],
    targets: List[Union[int, float]]
):
    """
    This is a recursive function that interpolates values in a multidimßensional table.
    """
    current_input = input_names[index]
    results = []
    for interp_data_set in interp_data_sets:
        targets[index], next_interp_data_sets = find_nearest_arrays(
            data=interp_data_set,
            target=targets[index],
            attr_name=current_input
        )
        if not current_input == input_names[-1]:
            deeper_layer_results_list = recursive_data_interpolation(
                input_names=input_names,
                index=index + 1,
                output_names=output_names,
                interp_data_sets=next_interp_data_sets,
                targets=targets
            )

            deeper_layer_results_dict = {
                key: [
                    deeper_layer_result[key] for deeper_layer_result in deeper_layer_results_list
                ] for key in output_names
            }

        else:

            deeper_layer_results_dict = {
                key: [
                    getattr(data_set[0], key) for data_set in next_interp_data_sets
                ] for key in output_names
            }

        result = {}
        if len(deeper_layer_results_dict[output_names[0]]) == 2:
            for output_name, deeper_layer_results in deeper_layer_results_dict.items():
                result[output_name] = linear_interpolation(
                    x1=getattr(next_interp_data_sets[0][0], current_input),
                    y1=deeper_layer_results[0],
                    x2=getattr(next_interp_data_sets[1][0], current_input),
                    y2=deeper_layer_results[1],
                    x_target=targets[index]
                )
        else:
            for output_name, deeper_layer_results in deeper_layer_results_dict.items():
                result[output_name] = deeper_layer_results[0]

        results.append(result)

    return results


def get_cruise_data(
        profile_id: int,
        weight_lb: int,
        pressure_alt_ft: int,
        temperature_c: int,
        bhp_percent: int,
        db_session: Session) -> Dict[str, Union[int, float]]:
    """
    This function performs a table lookup operation, and returns 
    the cruise data.

    Parameters:
    - profile_id (int): aircraft performance profile id.
    - weight_lb (int): weight of the aircraft in lbs.
    - pressure_alt (int): pressure altitude in ft.
    - temperature (int): temperature in deg C.
    - bhp (int): break horsepower of the engine in %.
    - db_session (Session): an sqlalchemy database session, to wuery the database.

    Returns:
    - (dict): dictionary with 'ktas'(int), 'gph'(float) and 'rpm'(int) data.
    """
    # define list of inputs and outputs to loop trhough, and the result dictionary
    inputs = ["weight_lb", "pressure_alt_ft", "temperature_c", "bhp_percent"]
    input_targets = [weight_lb, pressure_alt_ft, temperature_c, bhp_percent]
    outputs = ["gph", "rpm", "ktas"]
    result = {}

    # Get table data
    table_data = db_session.query(models.CruisePerformance).filter(
        models.CruisePerformance.performance_profile_id == profile_id
    ).order_by(
        models.CruisePerformance.weight_lb,
        models.CruisePerformance.pressure_alt_ft,
        models.CruisePerformance.temperature_c,
        models.CruisePerformance.bhp_percent
    ).all()

    result = recursive_data_interpolation(
        input_names=inputs,
        index=0,
        output_names=outputs,
        interp_data_sets=[table_data],
        targets=input_targets
    )[0]

    print(result)

    return result


# pylint: disable=pointless-string-statement
# pylint: disable=unreachable
    '''
    weight_lb, weight_interp_data_sets =  find_nearest_arrays(
        data=table_data, 
        target=weight_lb, 
        attr_name="weight_lb"
    )
    weight_results = []
    for weight_data_set in weight_interp_data_sets:
        pressure_alt_ft, press_interp_data_sets =  find_nearest_arrays(
            data=weight_data_set, 
            target=pressure_alt_ft, 
            attr_name="pressure_alt_ft"
        )
        pressure_results = []
        for pressure_data_set in press_interp_data_sets:
            temperature_c, temp_interp_data_sets =  find_nearest_arrays(
                data=pressure_data_set, 
                target=temperature_c, 
                attr_name="temperature_c"
            )
            temperature_results = []
            for temperature_data_set in temp_interp_data_sets:
                bhp_percent, bhp_interp_data_sets =  find_nearest_arrays(
                    data=temperature_data_set, 
                    target=bhp_percent, 
                    attr_name="bhp_percent"
                )
                if len(bhp_interp_data_sets) == 2:
                    temperature_results.append(
                        linear_interpolation(
                            x1=bhp_interp_data_sets[0].bhp_percent, 
                            y1=bhp_interp_data_sets[0].ktas,
                            x2=bhp_interp_data_sets[1].bhp_percent, 
                            y2=bhp_interp_data_sets[1].ktas, 
                            x_target=bhp_percent
                        )
                    )
                else: 
                    temperature_results.append(bhp_interp_data_sets[0].ktas)

            if len(temp_interp_data_sets) == 2:
                pressure_results.append(
                    linear_interpolation(
                        x1=temp_interp_data_sets[0][0].temperature_c, 
                        y1=temperature_results[0],
                        x2=temp_interp_data_sets[1][0].temperature_c, 
                        y2=temperature_results[1], 
                        x_target=temperature_c
                    )
                )
            else: 
                pressure_results.append(temperature_results[0])
    
    '''


# pylint: disable=pointless-string-statement
# pylint: disable=unreachable
'''

def get_cruise_data(
        profile_id: int,
        weight_lb: int,
        pressure_alt_ft: int,
        temperature_c: int,
        bhp_percent: int,
        db_session: Session) -> Dict[str, Union[int, float]]:
    """
    This function performs a table lookup operation, and returns 
    the cruise data.

    Parameters:
    - profile_id (int): aircraft performance profile id.
    - weight_lb (int): weight of the aircraft in lbs.
    - pressure_alt (int): pressure altitude in ft.
    - temperature (int): temperature in deg C.
    - bhp (int): break horsepower of the engine in %.
    - db_session (Session): an sqlalchemy database session, to wuery the database.

    Returns:
    - (dict): dictionary with 'ktas'(int), 'gph'(float) and 'rpm'(int) data.
    """

    # Get table data
    table_data = db_session.query(models.CruisePerformance).filter(
        models.CruisePerformance.performance_profile_id == profile_id
    ).order_by(
        models.CruisePerformance.weight_lb,
        models.CruisePerformance.pressure_alt_ft,
        models.CruisePerformance.temperature_c,
        models.CruisePerformance.bhp_percent
    ).all()
    include_weight = len({row.weight_lb for row in table_data}) > 1

    # Check weight is within range
    if include_weight:

    # Check pressure is within range

    # Check temperature is within range

    # Check BHP is within range

    # Process output data
    gph_values = []
    rpm_values = []
    ktas_values = []
    for data_point in table_data:
        gph_values.append(data_point.gph)
        rpm_values.append(data_point.rpm)
        ktas_values.append(data_point.ktas)

    output_data = {
        'ktas': np.array(ktas_values),
        'gph': np.array(gph_values),
        'rpm': np.array(rpm_values)
    }

    round_digits = {'ktas': 0, 'gph': 2, 'rpm': 0}

    # Process input data
    if include_weight:
        input_data = [(
            row.weight_lb,
            row.pressure_alt_ft,
            row.temperature_c,
            row.bhp_percent
        ) for row in table_data]
        target = (weight_lb, pressure_alt_ft, temperature_c, bhp_percent)
    else:
        input_data = [(
            row.pressure_alt_ft,
            row.temperature_c,
            row.bhp_percent
        ) for row in table_data]
        target = (pressure_alt_ft, temperature_c, bhp_percent)

    # Interpolate
    result = {}
    for key, value in output_data.items():
        interp = LinearNDInterpolator(input_data, value)
        result[key] = round(interp(*np.meshgrid(*target))[0][0][0],
                            round_digits[key])

    print(result)
    return result
'''
