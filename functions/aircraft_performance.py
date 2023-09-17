"""
Useful Functions to Extract Aircraft Performance Data

Usage: 
- Import the required function and call it.
"""

from typing import Dict, Union, Any, List


from sqlalchemy.orm import Session

import models


def linear_interpolation(
    x1: Union[int, float],
    y1: Union[int, float],
    x2: Union[int, float],
    y2: Union[int, float],
    x_target: Union[int, float]
) -> Union[int, float]:
    """
    This function performs a 1-dimensional linear interpolation
    """

    # Calculate the slope
    slope = (y2 - y1) / (x2 - x1)

    # Use the slope to find the interpolated y-value at x_target
    y_target = y1 + slope * (x_target - x1)

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
    This is a recursive function that interpolates values in a multidimensional table.
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


def get_landing_takeoff_data(
    profile_id: int,
    is_takeoff: bool,
    weight_lb: int,
    pressure_alt_ft: int,
    temperature_c: int,
    runway_surface_id: int,
    head_wind: float,
    db_session: Session
) -> Dict[str, Union[int, float]]:
    """
    This function performs a table lookup operation, and returns 
    the takeoff or landing data (ground_roll_ft and obstacle_clearance_ft).
    """
    # define list of inputs and outputs to loop trhough
    inputs = ["weight_lb", "pressure_alt_ft", "temperature_c"]
    input_targets = [weight_lb, pressure_alt_ft, temperature_c]
    outputs = ["ground_roll", "obstacle_clearance_ft"]

    # Get table data
    if is_takeoff:
        table_data = db_session.query(models.TakeoffPerformance).filter(
            models.TakeoffPerformance.performance_profile_id == profile_id
        ).order_by(
            models.TakeoffPerformance.weight_lb,
            models.TakeoffPerformance.pressure_alt_ft,
            models.TakeoffPerformance.temperature_c
        ).all()
    else:
        table_data = db_session.query(models.LandingPerformance).filter(
            models.LandingPerformance.performance_profile_id == profile_id
        ).order_by(
            models.LandingPerformance.weight_lb,
            models.LandingPerformance.pressure_alt_ft,
            models.LandingPerformance.temperature_c
        ).all()

    # Get table data results
    result = recursive_data_interpolation(
        input_names=inputs,
        index=0,
        output_names=outputs,
        interp_data_sets=[table_data],
        targets=input_targets
    )[0]

    # Pre-process table data results

    return result


def get_cruise_data(
    profile_id: int,
    weight_lb: int,
    pressure_alt_ft: int,
    temperature_c: int,
    bhp_percent: int,
    db_session: Session
) -> Dict[str, Union[int, float]]:
    """
    This function performs a table lookup operation, and returns 
    the cruise data (ktas, gph, rpm).
    """

    # define list of inputs and outputs to loop trhough
    inputs = ["weight_lb", "pressure_alt_ft", "temperature_c", "bhp_percent"]
    input_targets = [weight_lb, pressure_alt_ft, temperature_c, bhp_percent]
    outputs = ["ktas", "gph", "rpm"]

    # Get table data
    table_data = db_session.query(models.CruisePerformance).filter(
        models.CruisePerformance.performance_profile_id == profile_id
    ).order_by(
        models.CruisePerformance.weight_lb,
        models.CruisePerformance.pressure_alt_ft,
        models.CruisePerformance.temperature_c,
        models.CruisePerformance.bhp_percent
    ).all()

    # Get table data results
    result = recursive_data_interpolation(
        input_names=inputs,
        index=0,
        output_names=outputs,
        interp_data_sets=[table_data],
        targets=input_targets
    )[0]

    # Pre-process table data results
    result["ktas"] = int(round(result["ktas"], 0))
    result["gph"] = float(round(result["gph"], 2))
    result["rpm"] = int(round(result["rpm"], 0))

    return result
