import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faStar } from '@fortawesome/free-solid-svg-icons';
import { faStar as farStar } from '@fortawesome/free-regular-svg-icons';

interface Review {
    _id: string;
    user_id: string;
    business_id: string;
    user_name?: string;
    business_name?: string;
    business_city?: string;
    stars: number;
    text: string;
    date: string;
}

interface ReviewCardProps {
    review: Review;
    isUser: boolean;
}

export default function ReviewCard({ review, isUser }: ReviewCardProps) {
    // create stars for review
    const stars = Array.from({ length: review.stars }, (_, i) => (
        <FontAwesomeIcon key={i} icon={faStar} className="text-yellow-300" />
    ));

    // create empty stars for review
    const emptyStars = Array.from({ length: 5 - review.stars }, (_, i) => (
        <FontAwesomeIcon key={i} icon={farStar} className="text-yellow-300" />
    ));

    return (
        <div className="h-full p-4 my-2 bg-white shadow-md rounded-lg flex flex-row justify-between items-start">
            <div className="w-4/5">
                <h3 className="text-lg text-justify font-medium">
                    {review.text}
                </h3>
            </div>
            <div className="w-1/5 pl-5 h-full flex flex-col items-end justify-between">
                <div className="flex flex-col items-end">
                    {isUser ? (
                        <p className="mt-2 text-lg text-gray-800 text-end">
                            {review.business_name}, {review.business_city}
                        </p>
                    ) : (
                        <p className="mt-2 text-lg text-gray-800 text-end">
                            {review.user_name}
                        </p>
                    )}
                    <p className="text-lg font-medium text-yellow-500">
                        {stars}
                        {emptyStars}
                    </p>
                </div>
                <p className="mt-2 text-sm text-gray-500">
                    {review.date ? new Date(review.date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : ''}
                </p>
            </div>
        </div>
    );
}